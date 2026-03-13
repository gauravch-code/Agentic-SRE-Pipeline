package main

import (
	"fmt"
	"runtime"
	"time"
)

func main() {
	for {
		fmt.Printf("🤖 Cloud Agent Online. Running natively on: %s\n", runtime.GOOS)
		time.Sleep(2 * time.Second)
	}
}
