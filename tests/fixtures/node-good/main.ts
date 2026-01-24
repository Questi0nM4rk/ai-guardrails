/**
 * Good TypeScript code - should pass biome and tsc strict mode.
 *
 * This module demonstrates proper TypeScript code style with:
 * - Explicit type annotations
 * - No any types
 * - Proper null handling
 */

/**
 * Process a list of numbers by doubling each value.
 * @param data - Array of numbers to process
 * @returns A new array with each value doubled
 */
function process(data: number[]): number[] {
	return data.map((x) => x * 2);
}

/**
 * Calculate the sum of two numbers.
 * @param x - First number
 * @param y - Second number
 * @returns The sum of x and y
 */
function calculate(x: number, y: number): number {
	return x + y;
}

/**
 * Get a value from a predefined map.
 * @param key - The key to look up
 * @param defaultValue - Value to return if key not found
 * @returns The value associated with the key, or the default
 */
function getValue(key: string, defaultValue: number): number {
	const map: Record<string, number> = { a: 1, b: 2 };
	return map[key] ?? defaultValue;
}

/**
 * Example function demonstrating proper variable usage.
 * @returns A greeting string
 */
function example(): string {
	const result = "hello";
	return result;
}

/** User data structure */
interface User {
	name: string;
	age: number;
}

const user: User = {
	name: "Alice",
	age: 30,
};

/**
 * Safely get an element by ID.
 * @param id - The element ID to find
 * @returns The element or null if not found
 */
function getElement(id: string): HTMLElement | null {
	return document.getElementById(id);
}

/**
 * Check if two strings are equal using strict equality.
 * @param a - First string
 * @param b - Second string
 * @returns True if strings are equal
 */
function isEqual(a: string, b: string): boolean {
	return a === b;
}

export { calculate, example, getElement, getValue, isEqual, process, user };
export type { User };
