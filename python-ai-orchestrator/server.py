import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
# Notice we dropped LangChain and imported LLM directly from crewai!
from crewai import Agent, Task, Crew, Process, LLM

# 1. Load the API key from the .env file
load_dotenv()

app = Flask(__name__)

# 2. Initialize the Gemini LLM using CrewAI's native wrapper
# The "gemini/" prefix tells the engine exactly which cloud provider to route to
llm = LLM(
    model="gemini/gemini-2.5-flash",
    temperature=0.1
)

@app.route('/alert', methods=['POST'])
def receive_alert():
    data = request.json
    pod_name = data.get('pod_name', 'Unknown-Pod')
    memory_bytes = data.get('memory_bytes', 0)
    
    print("\n" + "="*50)
    print("🚨 INCOMING ALERT FROM KUBERNETES 🚨")
    print(f"Pod Name: {pod_name}")
    print(f"Memory Spiked To: {memory_bytes} bytes")
    print("🧠 Waking up AI Agent to investigate...")
    print("="*50 + "\n")
    
    # 3. Define the Agent (The Persona)
    sre_agent = Agent(
        role='Senior Kubernetes SRE',
        goal='Diagnose Kubernetes pod memory spikes and provide actionable kubectl remediation commands.',
        backstory='You are a veteran Site Reliability Engineer managing massive Kubernetes clusters. You excel at taking raw metric alerts and translating them into safe, effective mitigation commands.',
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    # 4. Define the Task (The Job)
    diagnosis_task = Task(
        description=f'The pod {pod_name} just spiked to {memory_bytes} bytes of memory usage. This exceeds our 8MB threshold. Briefly explain why a lightweight Go container might spike in memory, and then output the exact kubectl command needed to restart the deployment named "sre-agent-deployment" in the "default" namespace.',
        expected_output='A brief diagnosis of the memory spike and the exact kubectl rollout restart command.',
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