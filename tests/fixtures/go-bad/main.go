// Bad Go code - should fail gofmt and go vet

package main

import (
"fmt"
    "os"   // Wrong indentation
)

// Missing comment on exported function
func Process(data []int) []int  {
result := []int{}  // Should use make or append
for _, v := range data{  // Missing space before brace
result = append(result,v*2)  // Missing space after comma
}
return result
}

// Unreachable code
func Calculate(x, y int) int {
    return x + y
    fmt.Println("unreachable")  // This will never execute
}

// Missing error check
func readFile(path string) string {
    data, _ := os.ReadFile(path)  // Ignoring error
    return string(data)
}

// Unused variable
func getValue(key string) int {
    unused := 42  // Never used
    m := map[string]int{"a": 1, "b": 2}
    return m[key]
}

// Printf format error
func logMessage(name string, count int) {
    fmt.Printf("User %d has %s items\n", name, count)  // Wrong format verbs
}

func main() {
fmt.Println("hello")
}
