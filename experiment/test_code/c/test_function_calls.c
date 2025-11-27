#include <stdio.h>

// Function declaration
int add(int a, int b);
int multiply(int a, int b);
void print_result(int result);
int calculate_complex(int x, int y, int z);

int main() {
    int a = 5;
    int b = 10;
    int c = 3;
    
    // Call functions to test relationships
    int sum = add(a, b);
    int product = multiply(sum, c);
    print_result(product);
    
    int complex = calculate_complex(a, b, c);
    print_result(complex);
    
    return 0;
}

int add(int a, int b) {
    return a + b;
}

int multiply(int a, int b) {
    return a * b;
}

void print_result(int result) {
    printf("Result: %d\n", result);
}

int calculate_complex(int x, int y, int z) {
    int temp = add(x, y);      // main -> add
    int temp2 = multiply(temp, z);  // main -> multiply (indirectly), calculate_complex -> multiply
    return add(temp2, 1);      // calculate_complex -> add
}