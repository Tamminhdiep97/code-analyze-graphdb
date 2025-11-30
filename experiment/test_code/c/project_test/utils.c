#include <stdio.h>
#include "utils.h"

// Function definitions
void print_result(int result) {
    printf("The result is: %d\n", result);
}

int safe_divide(int a, int b, int *result) {
    if (b == 0) {
        return -1; // Division by zero error
    }
    *result = a / b;
    return 0; // Success
}