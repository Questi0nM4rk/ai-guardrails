package main

import "fmt"

func main() {
	fmt.Println("hello")
}

func BadFunction() {
	_ = fmt.Sprintf("%d", "not a number")
}
