package main

import (
	"context"
	"fmt"
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
)

func main() {
	fmt.Println(" In-Cluster Agent Online...")

	// 1. THE IN-CLUSTER AUTHENTICATION
	// We ask K8s for the mounted token!
	config, err := rest.InClusterConfig()
	if err != nil {
		panic(fmt.Errorf("fatal error getting in-cluster config: %v", err))
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		panic(err.Error())
	}

	fmt.Println("Successfully authenticated from INSIDE the cluster!")

	// 2. The Continuous Observation Loop
	for {
		pods, err := clientset.CoreV1().Pods("default").List(context.TODO(), metav1.ListOptions{})
		if err != nil {
			fmt.Printf("API Error: %v\n", err)
		} else {
			fmt.Printf("I can see %d pods running in my namespace!\n", len(pods.Items))
		}
		fetchPodMemory()

		time.Sleep(5 * time.Second) // Wait 5 seconds and check again
	}
}
