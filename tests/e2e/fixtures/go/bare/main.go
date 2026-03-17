package main

import "fmt"

func main() {
	unused := 42
	fmt.Println("hello")
}

func badFunc() error {
	return nil
}
