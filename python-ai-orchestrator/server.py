import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


# 1. Load the API key from the .env file
load_dotenv()

app = Flask(__name__)

# 2. Initialize the Gemini LLM using CrewAI's native wrapper
# The "gemini/" prefix tells the engine exactly which cloud provider to route to
llm = LLM(
    model="gemini/gemini-2.5-flash",
    temperature=0.1
)

class MCPQuerySchema(BaseModel):
    nl_query: str = Field(..., description="The plain English command for the Kubernetes cluster (e.g., 'Get logs for frontend pod' or 'Increase memory limit').")

class KubeMCPTool(BaseTool):
    name: str = "Kubernetes MCP Server"
    description: str = "Use this tool to interact with the Kubernetes cluster. It translates natural language into secure K8s API calls. Use it to read logs, check limits, or patch deployments."
    args_schema: type[BaseModel] = MCPQuerySchema

    def _run(self, nl_query: str) -> str:
        print(f"\n[TOOL TRIGGERED] AI sent NL query to Cluster: '{nl_query}'")

        mcp_server_url = "http://localhost:8080/mcp/query"
        payload = {
            "intent": nl_query
        }
        try:
            response = requests.post(mcp_server_url, json = payload, timeout = 15)
            response.raise_for_status()

            mcp_data = response.json()
            result = mcp_data.get("result", "No result returned from cluster.")
            print(f"[MCP SUCCESS]: Fata retrieved from cluster.")
            return result
        
        except requests.exceptions.RequestException as e:
            error_msg = f"[MCP NETWORK ERROR]: Failed to reach Kube MCP Server. Details: {e}"
            print(error_msg)
            return error_msg
    

@app.route('/alert', methods=['POST'])
def receive_alert():
    data = request.json
    pod_name = data.get('pod_name', 'Unknown-Pod')
    
    print(f"\n🚨 ALERT TRIPPED: Potential issue in pod {pod_name}. Waking AI...\n")

    mcp_tool = KubeMCPTool()
    
    # 3. Define the Agent (The Persona)
    sre_agent = Agent(
        role='Autonomous Kubernetes SRE',
        goal='Investigate cluster alerts and fix them dynamically using your Kube MCP Tool.',
        backstory='You are an elite SRE. You do not just guess commands; you actively use your MCP tool to inspect the cluster, read logs, and execute safe patches.',
        verbose=True,
        allow_delegation=False,
        llm=llm,
        tools=[mcp_tool]
    )

    # 4. Define the Task (The Job)
    diagnosis_task = Task(
        description=f'''
        URGENT ALERT: The pod '{pod_name}' is experiencing a critical issue. 
        
        YOUR MISSION:
        1. Use your Kube MCP Tool to ask for the current memory limits of '{pod_name}'.
        2. Use the tool again to ask for the last 20 lines of logs to confirm why it is failing.
        3. Use the tool a final time to patch the deployment and increase its memory limit to 512Mi.
        
        Do not output raw code. Execute the investigation and the fix yourself using the tool.
        ''',
        expected_output='A summary of the actions you took using the MCP tool and confirmation that the cluster is stable.',
        agent=sre_agent
    )

    # 5. Form the Crew and execute
    sre_crew = Crew(
        agents=[sre_agent],
        tasks=[diagnosis_task],
        process=Process.sequential
    )

    print("⏳ AI is thinking...\n")
    result = sre_crew.kickoff()
    
    print("\n" + "="*50)
    print("✅ AI DIAGNOSIS & REMEDIATION PLAN ✅")
    print(result)
    print("="*50 + "\n")

    return jsonify({"status": "Alert processed", "ai_response": str(result)}), 200

if __name__ == '__main__':
    print("🤖 AI Orchestrator listening on port 5000...")
    app.run(host='0.0.0.0', port=5000)