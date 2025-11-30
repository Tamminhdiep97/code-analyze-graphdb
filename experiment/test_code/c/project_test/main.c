#include <stdio.h>
#include "math_operations.h"
#include "utils.h"

int main() {
    int a = 5;
    int b = 10;
    int c = 3;

    // Use functions from math_operations.c
    int sum = add(a, b);
    print_result(sum);  // Use function from utils.c

    int product = multiply(sum, c);
    print_result(product);

    int complex_result = calculate_complex(a, b, c);
    print_result(complex_result);

    // Test utility function
    int division_result;
    int status = safe_divide(product, 2, &division_result);
    if (status == 0) {
        print_result(division_result);
    } else {
        printf("Division failed!\n");
    }

    return 0;
}