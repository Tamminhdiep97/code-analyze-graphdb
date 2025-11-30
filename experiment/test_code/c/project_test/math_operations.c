#include "math_operations.h"

// Function definitions
int add(int a, int b) {
    return a + b;
}

int multiply(int a, int b) {
    return a * b;
}

int calculate_complex(int x, int y, int z) {
    int temp = add(x, y);      // calls function from same file (or linked)
    int temp2 = multiply(temp, z);  // calls another function from same file
    return add(temp2, 1);      // calls function from same file
}