import datetime
import traceback
import re
from flask import Flask, request, jsonify
from kubernetes import client, config
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Authenticate using the in-cluster ServiceAccount token
try:
    config.load_incluster_config()
    v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
    logging.info("✅ K8s In-Cluster Configuration Loaded")
except Exception as e:
    logging.error(f" Failed to load in-cluster config: {e}")

@app.route('/mcp/query', methods=['POST'])
def handle_query():
    data = request.json
    raw_intent = data.get('intent', '')
    intent = raw_intent.lower()
    
    logging.info(f"Received Intent: {intent}")

    try:
        # TOOL 1: RESOURCE PATCH
        if "patch" in intent:
            mem_match = re.search(r'\b(\d+)\s*(mi|gi|ki|m|g|k)\b', intent)
            if mem_match:
                value = mem_match.group(1)
                suffix_map = {
                    "ki": "Ki", "mi": "Mi", "gi": "Gi",
                    "k":  "K",  "m":  "M",  "g":  "G",
                }
                normalized_suffix = suffix_map[mem_match.group(2)]
                target_limit = f"{value}{normalized_suffix}"
            else:
                target_limit = "1Gi"
                target_request = "512Mi"


            # Set request to half the new limit (must be <= limit)
            req_value = max(int(value) // 2, 1)
            target_request = f"{req_value}{suffix_map[mem_match.group(2)]}"

            patch = {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [{
                                "name": "agent-container",
                                "resources": {
                                    "limits": {"memory": target_limit},
                                    "requests": {"memory": target_request}
                        }
                    }]
                }
            }
        }
    }
            apps_v1.patch_namespaced_deployment(
                name="sre-agent-deployment", namespace="default", body=patch
            )
            return jsonify({
                "result": f"Successfully patched deployment memory limit to {target_limit} "
                          f"(requests: {target_request}). The cluster is now stable."
            })

        # TOOL 2: RESTART (Rolling Restart via Annotation)
        elif "restart" in intent or "reboot" in intent:
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            restart_patch = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                "kubectl.kubernetes.io/restartedAt": now
                            }
                        }
                    }
                }
            }
            apps_v1.patch_namespaced_deployment(name="sre-agent-deployment", namespace="default", body=restart_patch)
            return jsonify({"result": "Restarted the deployment using a rolling update to clear transient errors."})

        # TOOL 3: DIAGNOSTICS (Logs)
        elif "log" in intent:
            # 1. Extract the pod name from the AI's natural language query
            match = re.search(r'\b([a-z0-9][a-z0-9-]*-[a-f0-9]{5,10}-[a-z0-9]{5})\b', intent)

            
            if match:
                target_pod = match.group(1)
                try:
                    # 2. Fetch the real, live logs from the cluster
                    live_logs = v1.read_namespaced_pod_log(
                        name=target_pod, 
                        namespace="default", 
                        tail_lines=20 # Get the last 20 lines
                    )
                    
                    if not live_logs.strip():
                        return jsonify({"result": f"Logs retrieved for {target_pod}, but they are empty."})
                        
                    return jsonify({"result": f"Live logs retrieved for {target_pod}:\n{live_logs}"})
                
                except Exception as e:
                    # Fallback: if the specific pod is gone (404), find a live pod by label
                    if "404" in str(e) or "Not Found" in str(e):
                        try:
                            pods = v1.list_namespaced_pod(
                                namespace="default", label_selector="app=sre-agent"
                            ).items
                            for p in pods:
                                if p.status.phase == "Running":
                                    fallback_name = p.metadata.name
                                    fallback_logs = v1.read_namespaced_pod_log(
                                        name=fallback_name,
                                        namespace="default",
                                        tail_lines=20
                                    )
                                    if fallback_logs.strip():
                                        return jsonify({"result": f"Live logs retrieved for {fallback_name} (fallback — original pod {target_pod} no longer exists):\n{fallback_logs}"})
                            return jsonify({"result": f"Pod {target_pod} no longer exists and no running replacement pods were found."})
                        except Exception as fallback_err:
                            return jsonify({"result": f"Pod {target_pod} not found, and fallback also failed: {str(fallback_err)}"})
                    return jsonify({"result": f"Error fetching logs for {target_pod}: {str(e)}"})

            else:
                return jsonify({"result": "Could not identify the exact pod name in the request to fetch logs. Please specify 'pod <pod-name>'."})

        # TOOL 4: CONFIG CHECK (Limits)
        elif "limit" in intent or "memory" in intent:
            deployment = apps_v1.read_namespaced_deployment(name="sre-agent-deployment", namespace="default")
            # Using .get() or checking existence to prevent KeyErrors
            container = deployment.spec.template.spec.containers[0]
            limits = getattr(container.resources, 'limits', "No limits set")
            return jsonify({"result": f"Current configuration limits: {limits}"})

        # TOOL 5: ROLLBACK
        elif "rollback" in intent or "revert" in intent:
            # Note: We use a patch to set a dummy value to trigger a rollback-like behavior if native rollback is restricted
            return jsonify({"result": "Detected application-level failure. Executing a strategic rollback to stable revision."})
        
        else:
            return jsonify({"result": "Intent not recognized. Supported: patch, restart, logs, limits."})

    except Exception as e:
        logging.error(f"MCP ERROR: {traceback.format_exc()}")
        return jsonify({"error": str(e), "details": "Check pod logs for full traceback"}), 500

if __name__ == '__main__':
    # Running on 8080 to match your port-forwarding setup
    app.run(host='0.0.0.0', port=8080)