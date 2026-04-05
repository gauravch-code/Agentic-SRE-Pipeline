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
	fmt.Println("📈 Auto-Scaler Agent Online...")

	// 1. Authentication Engine (You are a pro at this now)
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

	// 2. THE TARGET: Grab the Deployment from the cluster
	deploymentName := "sre-agent-deployment"
	deploymentsClient := clientset.AppsV1().Deployments("default")

	// We use .Get() instead of .List() because we know exactly which one we want.
	deployment, err := deploymentsClient.Get(context.TODO(), deploymentName, metav1.GetOptions{})
	if err != nil {
		panic(fmt.Errorf("failed to get deployment: %v", err))
	}

	fmt.Printf("✅ Found Deployment: %s\n", deployment.Name)
	fmt.Printf("Current Replicas: %d\n", *deployment.Spec.Replicas)

	// 3. THE MUTATION
	// TODO: Create a new int32 variable set to 3.
	// newReplicas := int32(3)
	newReplicas := int32(3)
	// TODO: Point the deployment's replica count to your new variable.
	// deployment.Spec.Replicas = &newReplicas
	deployment.Spec.Replicas = &newReplicas

	fmt.Println("⚡ Pushing updated blueprint to the cluster...")

	// 4. THE UPDATE
	// TODO: Call deploymentsClient.Update(...) to push the struct back to Kubernetes.
	// You must pass three arguments: context.TODO(), the deployment variable, and metav1.UpdateOptions{}
	// _, err = ...
	_, err = deploymentsClient.Update(context.TODO(), deployment, metav1.UpdateOptions{})
	if err != nil {
		panic(fmt.Errorf("failed to update deployment: %v", err))
	}

	fmt.Println("🚀 Deployment successfully scaled to 3 replicas!")
}
