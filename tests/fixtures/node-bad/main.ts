// Bad TypeScript code - should fail biome and tsc

// Using any type (noExplicitAny)
function process(data: any): any {
  return data.map((x: any) => x * 2);
}

// Console.log statements (not allowed)
function calculate(x: number, y: number): number {
  console.log("calculating...");
  return x + y;
}

// Missing return type
function getValue(key: string) {
  const map = { a: 1, b: 2 };
  return map[key];  // Implicit any from index signature
}

// Unused variable
function example() {
  const unused = 42;
  const result = "hello";
  return result;
}

// Inconsistent formatting and semicolons
const user = {
name: "Alice",
    age: 30
};

// Unsafe assertion
const element = document.getElementById("app") as HTMLDivElement;
element.innerHTML = "hello";  // Could be null

// == instead of ===
function isEqual(a: string, b: string): boolean {
  return a == b;
}

export { process, calculate, getValue, example, user, isEqual };
