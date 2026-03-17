package main

import "fmt"

func main() {
	fmt.Println("hello")
}

// Exported function with unexported return type (golangci-lint: revive/exported)
func BadFunction() {
	_ = fmt.Sprintf("%d", "not a number") // govet: printf arg mismatch
}
