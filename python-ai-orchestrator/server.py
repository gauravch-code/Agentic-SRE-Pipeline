import os
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# load the API key from the .env file
load_dotenv()

app = Flask(__name__)

# Global dictionary to track deployment cooldowns
# This is for ignoring duplicate alerts for 3 minutes
alert_cooldowns = {}
restart_history = {}

# initialize the Gemini LLM using CrewAI's native wrapper
llm = LLM(
    model="openai/gpt-4o-mini",
    temperature=0.1
)

# schema for the nl_query which the agent will send to the MCP server
class MCPQuerySchema(BaseModel):
    nl_query: str = Field(..., description="The plain English command for the Kubernetes cluster.")

# Agent will run this tool to connect to the MCP server
class KubeMCPTool(BaseTool):
    name: str = "Kubernetes MCP Server"
    description: str = "Use this tool to interact with the Kubernetes cluster. Translates NL to K8s API calls."
    args_schema: type[BaseModel] = MCPQuerySchema

    def _run(self, nl_query: str) -> str:
        print(f"\n[TOOL TRIGGERED] AI sent NL query: '{nl_query}'")
        mcp_server_url = "http://localhost:8080/mcp/query"
        payload = {"intent": nl_query}
        try:
            response = requests.post(mcp_server_url, json=payload, timeout=15)
            response.raise_for_status()
            mcp_data = response.json()
            result = mcp_data.get("result", "No result returned.")
            print(f"[MCP SUCCESS]: Data retrieved from cluster.")
            return result
        except requests.exceptions.RequestException as e:
            error_msg = f"[MCP NETWORK ERROR]: {e}"
            print(error_msg)
            return error_msg

@app.route('/alert', methods=['POST'])
def receive_alert():
    print(f"\n[NETWORK DEBUG] ⚡ HTTP POST received from the cluster!")
    data = request.json
    pod_name = data.get('pod_name', 'Unknown-Pod')
    
    parts = pod_name.split("-")
    if len(parts) > 2:
        deployment_name = "-".join(parts[:-2])
    else:
        deployment_name = pod_name

    current_time = time.time()
    
    # Check if we are already investigating this deployment
    if deployment_name in alert_cooldowns:
        time_since_last = current_time - alert_cooldowns[deployment_name]
        if time_since_last < 30:  # 3 Minute Cooldown
            print(f" SILENCING: Already investigating {deployment_name}. Ignoring duplicate for {pod_name}.")
            return jsonify({"status": "ignored", "reason": "cooldown active"}), 200

    # Set the lock
    alert_cooldowns[deployment_name] = current_time

        # Compute escalation context: has this deployment been restarted recently?
    last_restart = restart_history.get(deployment_name)
    if last_restart is not None:
        seconds_since_restart = int(current_time - last_restart)
        if seconds_since_restart < 120:  # within 5 minutes
            escalation_context = (
                f"⚠️ CRITICAL ESCALATION CONTEXT: This deployment was restarted "
                f"by you just {seconds_since_restart} seconds ago, but the problem "
                f"has returned. A restart has been PROVEN ineffective for this "
                f"incident. You MUST NOT choose 'restart deployment' again. "
                f"You MUST escalate to 'patch memory' to permanently fix the issue."
            )
        else:
            escalation_context = (
                f"CONTEXT: This deployment was last restarted {seconds_since_restart // 60} "
                f"minutes ago — that fix appears to have held until now. Treat this as "
                f"a fresh incident."
            )
    else:
        escalation_context = (
            "CONTEXT: This is the first alert for this deployment. "
            "No prior remediation has been attempted."
        )

    
    print(f"\n ALERT TRIPPED: Potential issue in pod {pod_name}. Waking AI...\n")

    mcp_tool = KubeMCPTool()
    
    # Agent
    sre_agent = Agent(
        role='Autonomous Kubernetes SRE',
        goal='Investigate cluster alerts and fix them dynamically using your Kube MCP Tool.',
        backstory='You are an elite SRE. You use your MCP tool to inspect the cluster, read logs, and execute safe patches.',
        verbose=True,
        allow_delegation=False,
        llm=llm,
        tools=[mcp_tool]
    )

    diagnosis_task = Task(
    description=f'''
    The pod '{pod_name}' has triggered a memory alert (usage exceeded 80% of its limit).
    
    {escalation_context}
    
    DECISION RULES (apply in order, stop at first match):
    1. If the escalation context says a restart was PROVEN ineffective, use 'patch memory to <2x current limit>'.
    2. Otherwise, use 'restart deployment'.
    
    First, use your tool with 'get limits' to check the current limit.
    Then, use your tool with 'get logs for pod {pod_name}' to review recent activity.
    Then execute the appropriate action above.
    
    CRITICAL RESTRICTION: You are ONLY allowed to use these exact phrases with your tool:
    - 'get limits'
    - 'get logs for pod {pod_name}'
    - 'restart deployment'  
    - 'patch memory to <value>Mi'
    ''',
    expected_output='A summary of actions taken and the result of those actions. Then also, confirm the stability.',
    agent=sre_agent,
    tools=[mcp_tool]
)




    sre_crew = Crew(
        agents=[sre_agent],
        tasks=[diagnosis_task],
        process=Process.sequential
    )

    print("AI is thinking...\n")
    result = None
    for attempt in range(3):
        try:
            result = sre_crew.kickoff()
            break
        except Exception as e:
            if "503" in str(e) and attempt < 2:
                wait = 2 ** attempt
                print(f"Gemini 503 (attempt {attempt+1}/3). Retrying in {wait}s...")
                time.sleep(wait)
                continue
            raise


        # Track if the AI chose to restart — used for escalation on next alert
    result_text = str(result).lower()
    if ("restart" in result_text and "deploy" in result_text) and "patch" not in result_text:
        restart_history[deployment_name] = time.time()
        print(f" Recorded restart for {deployment_name} — will escalate if it alerts again within 5 min.")
    elif ("patch" in result_text and "memory" in result_text
      and "fail" not in result_text and "error" not in result_text):
        # Successful patch — clear any prior restart record since the issue is resolved
        restart_history.pop(deployment_name, None)
        print(f"Cleared restart history for {deployment_name} after successful patch.")

    
    print("\n" + "="*50)
    print("AI DIAGNOSIS & REMEDIATION PLAN")
    print(result)
    print("="*50 + "\n")

    return jsonify({"status": "Alert processed", "ai_response": str(result)}), 200

if __name__ == '__main__':
    print(" AI Orchestrator listening on port 5055...")
    app.run(host='0.0.0.0', port=5055)