package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"sync"
	"time"
)

type PromResponse struct {
	Data struct {
		Result []struct {
			Metric map[string]string `json:"metric"`
			Value  []interface{}     `json:"value"`
		} `json:"result"`
	} `json:"data"`
}

var (
	lastAlertTime = make(map[string]time.Time)
	mapMutex      = &sync.Mutex{}
)

func fetchPodMemory() {
	fmt.Println("🔍 Querying Prometheus for memory metrics...")

	// Query 1: Current memory usage per pod
	usageQL := `sum by (pod) (
    container_memory_working_set_bytes{namespace="default", pod=~"sre-agent-deployment.*"}
    and on (pod) (time() - timestamp(kube_pod_info{namespace="default", pod=~"sre-agent-deployment.*"})) < 30
)`

	// Query 2: Memory limits per pod (set in deployment spec)
	limitsQL := `sum by (pod) (
    kube_pod_container_resource_limits{namespace="default", pod=~"sre-agent-deployment.*", resource="memory"}
)`

	usageData := queryPrometheus(usageQL)
	limitsData := queryPrometheus(limitsQL)

	if usageData == nil || limitsData == nil {
		return
	}

	// Build a map of pod -> limit bytes
	limitMap := make(map[string]int)
	for _, result := range limitsData.Data.Result {
		podName := result.Metric["pod"]
		limitStr := fmt.Sprintf("%v", result.Value[1])
		limitInt, _ := strconv.Atoi(limitStr)
		limitMap[podName] = limitInt
	}

	for _, result := range usageData.Data.Result {
		podName := result.Metric["pod"]
		memStr := fmt.Sprintf("%v", result.Value[1])
		memInt, _ := strconv.Atoi(memStr)

		limitInt, hasLimit := limitMap[podName]
		if !hasLimit || limitInt == 0 {
			fmt.Printf("⚠️ No limit found for pod %s, skipping\n", podName)
			continue
		}

		percentage := float64(memInt) / float64(limitInt) * 100

		// Only alert when usage exceeds 80% of the limit
		if percentage > 80.0 {
			fmt.Printf("⚠️ WARNING: Pod %s is at %.1f%% memory (%d / %d bytes)\n",
				podName, percentage, memInt, limitInt)

			mapMutex.Lock()
			lastTime, exists := lastAlertTime[podName]

			if exists && time.Since(lastTime) < 30*time.Second {
				fmt.Printf("Cooldown active for %s\n", podName)
				mapMutex.Unlock()
				continue
			}

			lastAlertTime[podName] = time.Now()
			mapMutex.Unlock()

			go func(pName string) {
				jsonPayload, _ := json.Marshal(map[string]string{
					"pod_name": pName,
					"alert":    "OOM_RISK",
				})

				alertURL := "http://host.docker.internal:5055/alert"
				fmt.Printf("Firing tripwire for %s...\n", pName)
				resp, err := http.Post(alertURL, "application/json", bytes.NewBuffer(jsonPayload))
				if err != nil {
					fmt.Printf("Failed to reach AI Orchestrator: %v\n", err)
				} else {
					fmt.Printf("Alert sent. Status: %s\n", resp.Status)
					resp.Body.Close()
				}
			}(podName)
		}
	}
}

// queryPrometheus is a helper that executes a PromQL query and returns the parsed response
func queryPrometheus(promQL string) *PromResponse {
	encodedQuery := url.QueryEscape(promQL)
	promURL := fmt.Sprintf("http://local-prom-prometheus-server.default.svc.cluster.local:80/api/v1/query?query=%s", encodedQuery)

	resp, err := http.Get(promURL)
	if err != nil {
		fmt.Printf("Failed to reach Prometheus: %v\n", err)
		return nil
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	var promData PromResponse
	json.Unmarshal(body, &promData)
	return &promData
}
