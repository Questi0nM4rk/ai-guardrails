// Package main demonstrates proper Go code style.
package main

import (
	"fmt"
	"os"
)

// Process doubles each value in the input slice.
func Process(data []int) []int {
	result := make([]int, 0, len(data))
	for _, v := range data {
		result = append(result, v*2)
	}
	return result
}

// Calculate returns the sum of two integers.
func Calculate(x, y int) int {
	return x + y
}

// ReadFile reads and returns the contents of a file.
// Returns an error if the file cannot be read.
func ReadFile(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("reading file: %w", err)
	}
	return string(data), nil
}

// GetValue retrieves a value from a map with a default.
func GetValue(key string, defaultVal int) int {
	m := map[string]int{"a": 1, "b": 2}
	if val, ok := m[key]; ok {
		return val
	}
	return defaultVal
}

// LogMessage prints a formatted message about a user.
func LogMessage(name string, count int) {
	fmt.Printf("User %s has %d items\n", name, count)
}

func main() {
	result := Process([]int{1, 2, 3})
	fmt.Println(result)
}
