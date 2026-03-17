#include <iostream>
int main() {
    int* ptr = new int(42);
    std::cout << *ptr << std::endl;
    return 0;
}
