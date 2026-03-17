package main

import (
	"errors"
	"fmt"
	"os"
)

func main() {
	// govet: printf verb mismatch — %d with string arg
	fmt.Printf("%d\n", "not a number")
}

func riskyOp() error {
	return errors.New("something went wrong")
}

func caller() {
	// errcheck: unchecked error return
	os.Remove("/tmp/testfile")
}
