from flask import Flask, request, jsonify
from kubernetes import client, config
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Authenticate using the in-cluster ServiceAccount token!
try:
    config.load_incluster_config()
    v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
except Exception as e:
    logging.error(f"Failed to load in-cluster config: {e}")

@app.route('/mcp/query', methods=['POST'])
def handle_query():
    data = request.json
    intent = data.get('intent', '').lower()
    logging.info(f"Received NL Query Intent: {intent}")

    try:
        # 1. Handle PATCH first (so the word 'memory' doesn't hijack it)
        if "patch" in intent or "increase" in intent:
            patch = {"spec": {"template": {"spec": {"containers": [{"name": "nginx", "resources": {"limits": {"memory": "512Mi"}}}]}}}}
            apps_v1.patch_namespaced_deployment(name="sre-agent-deployment", namespace="default", body=patch)
            return jsonify({"result": "Successfully patched deployment memory limit to 512Mi. The cluster is now stable."})

        # 2. Handle LOGS
        elif "log" in intent:
            # Simulating log retrieval for safety in this tutorial
            return jsonify({"result": "Logs retrieved: [ERROR] OutOfMemoryError. Container killed due to exceeding memory bounds."})

        # 3. Handle LIMITS
        elif "limit" in intent or "memory" in intent:
            deployment = apps_v1.read_namespaced_deployment(name="sre-agent-deployment", namespace="default")
            limits = deployment.spec.template.spec.containers[0].resources.limits
            # If limits are None, tell the AI that explicitly
            if limits is None:
                return jsonify({"result": "No memory limits are currently set for this deployment."})
            return jsonify({"result": f"Current limits: {limits}"})

        else:
            return jsonify({"result": "Intent not recognized by this MCP server."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)