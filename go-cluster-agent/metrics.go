package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
)

// 1. THE JSON BLUEPRINT
// Prometheus returns a deeply nested JSON object.
// We create Go structs so the compiler knows exactly how to read it.
type PromResponse struct {
	Data struct {
		Result []struct {
			Metric map[string]string `json:"metric"`
			Value  []interface{}     `json:"value"` // The actual metric value is hidden here
		} `json:"result"`
	} `json:"data"`
}

// 2. THE FETCH FUNCTION
func fetchPodMemory() {
	fmt.Println("🔍 Reaching out to Prometheus...")

	// The exact PromQL query we tested in the browser
	promQL := `sum(container_memory_working_set_bytes{namespace="default", pod=~"sre-agent-deployment.*"}) by (pod)`

	// URL-encode the query so it can be sent over HTTP
	encodedQuery := url.QueryEscape(promQL)

	// The internal Kubernetes DNS address for your Prometheus server
	promURL := fmt.Sprintf("http://local-prom-prometheus-server.default.svc.cluster.local:80/api/v1/query?query=%s", encodedQuery)

	// 3. THE HTTP REQUEST
	// TODO: Use http.Get(promURL) to send the request
	// resp, err := ...
	resp, err := http.Get(promURL)
	if err != nil {
		fmt.Printf("Failed to reach Prometheus: %v\n", err)
		return
	}
	defer resp.Body.Close()

	// if err != nil {
	// 	fmt.Printf("❌ Failed to reach Prometheus: %v\n", err)
	// 	return
	// }
	// defer resp.Body.Close()

	// 4. PARSING THE RESPONSE
	// body, _ := io.ReadAll(resp.Body)
	// var promData PromResponse
	body, _ := io.ReadAll(resp.Body)
	var promData PromResponse
	err = json.Unmarshal(body, &promData)

	// TODO: Use json.Unmarshal to translate the raw 'body' bytes into the 'promData' struct
	// err = ...
	if err != nil {
		fmt.Printf("Failed to parse JSON: %v\n", err)
		return
	}
	// if err != nil {
	// 	fmt.Printf("❌ Failed to parse JSON: %v\n", err)
	// 	return
	// }

	// 5. PRINTING THE RESULTS
	// for _, result := range promData.Data.Result {
	// 	podName := result.Metric["pod"]
	// 	memoryUsage := result.Value[1] // The value is the 2nd item in the array
	// 	fmt.Printf("📊 Pod: %s | Memory: %v bytes\n", podName, memoryUsage)
	// }

	// 5. PRINTING AND EVALUATING THE RESULTS
	for _, result := range promData.Data.Result {
		podName := result.Metric["pod"]

		// 1. Extract the memory value as a string, then convert to an integer
		memStr := fmt.Sprintf("%v", result.Value[1])

		// You will need to add "strconv" to your import list at the top of the file!
		memInt, _ := strconv.Atoi(memStr)

		// ==========================================
		// 🚨 YOUR CHALLENGE: WRITE THE LOGIC HERE
		// ==========================================
		// Write an if/else statement:
		// IF memInt is strictly greater than 8000000 (8 Megabytes):
		//    Print: "⚠️ WARNING: Pod [podName] is using high memory! ([memInt] bytes)"
		// ELSE:
		//    Print: "✅ Pod [podName] memory is stable at [memInt] bytes."
		// ==========================================

		if memInt > 8000000 {
			fmt.Printf("WARNING: Pod %v is using high memory!(%v bytes)\n", podName, memInt)

			// ==========================================
			// 🚨 NEW: THE WEBHOOK TO PYTHON
			// ==========================================
			// 1. Format the data as a JSON string
			jsonPayload := []byte(fmt.Sprintf(`{"pod_name": "%s", "memory_bytes": %d}`, podName, memInt))

			// 2. Fire the alert out of the cluster to your Windows machine on Port 5000
			alertURL := "http://host.docker.internal:5000/alert"
			resp, err := http.Post(alertURL, "application/json", bytes.NewBuffer(jsonPayload))

			if err != nil {
				fmt.Printf("❌ Failed to reach AI Orchestrator: %v\n", err)
			} else {
				fmt.Println("🚀 Alert successfully fired to Python AI!")
				resp.Body.Close()
			}
			// ==========================================

		} else {
			fmt.Printf("Pod: %v memory is stable at %v bytes.\n", podName, memInt)
		}

	}
}
