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
	fmt.Println("🔍 K8s Watcher Agent Initializing...")

	// 1. Find the Kubernetes config file on your machine
	var kubeconfig string
	if home := homedir.HomeDir(); home != "" {
		kubeconfig = filepath.Join(home, ".kube", "config")
	} else {
		fmt.Println("Error: Could not find home directory.")
		return
	}

	// 2. Build the configuration object from that file
	config, err := clientcmd.BuildConfigFromFlags("", kubeconfig)
	if err != nil {
		panic(err.Error())
	}

	// 3. Create the Clientset (The engine that talks to the K8s REST API)
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		panic(err.Error())
	}

	fmt.Println("✅ Successfully authenticated with Kubernetes API!")
	fmt.Println("👀 OBSERVE: Scanning for active pods in the 'default' namespace...\n")

	// 4. THE CHALLENGE: Ask the API for a list of pods!
	// TODO: Call clientset.CoreV1().Pods("default").List()
	// You need to pass context.TODO() and metav1.ListOptions{} as the two arguments.
	// pods, err := ...
	pods, err := clientset.CoreV1().Pods("default").List(context.TODO(), metav1.ListOptions{})

	if err != nil {
		panic(err.Error())
	}

	// 5. THE OUTPUT: Loop through the returned structs
	fmt.Printf("Found %d pods in the cluster:\n", len(pods.Items))
	for _, pod := range pods.Items {
		// TODO: Print the pod's Name and its Status Phase
		fmt.Printf("- %s (Status: %s)\n", pod.Name, pod.Status.Phase)
	}
}
