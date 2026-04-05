package main

import (
	"context"
	"fmt"
	"path/filepath"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/homedir"
)

func main() {
	fmt.Println("🪓 Executioner Agent Online...")

	// 1. Authentication Engine (Exact same as watcher.go)
	var kubeconfig string
	if home := homedir.HomeDir(); home != "" {
		kubeconfig = filepath.Join(home, ".kube", "config")
	}
	config, err := clientcmd.BuildConfigFromFlags("", kubeconfig)
	if err != nil {
		panic(err.Error())
	}
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		panic(err.Error())
	}

	// --- THE MUTATION LOGIC ---

	// 2. THE TARGET
	// TODO: Look at your previous terminal output.
	// Copy ONE of the exact pod names (e.g., "sre-agent-deployment-...") and paste it here.
	targetPod := "sre-agent-deployment-586d7ccbcd-jczqh"

	fmt.Printf("🎯 TARGET ACQUIRED: %s\n", targetPod)
	fmt.Println("⚡ Executing termination command...")

	// 3. THE ACTION
	// TODO: Call clientset.CoreV1().Pods("default").Delete(...)
	// You must pass three arguments: context.TODO(), the targetPod variable, and metav1.DeleteOptions{}
	// err = ...
	err = clientset.CoreV1().Pods("default").Delete(context.TODO(), targetPod, metav1.DeleteOptions{})

	if err != nil {
		fmt.Printf("Failed to terminate pod: %v\n", err)
		return
	}
	// if err != nil {
	// 	fmt.Printf("❌ Failed to terminate pod: %v\n", err)
	// 	return
	// }

	// fmt.Println("✅ Target successfully terminated.")
	fmt.Println("Deleted the target pod\n")
}
