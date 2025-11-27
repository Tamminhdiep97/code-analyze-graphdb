#include <stdio.h>
#include <string.h>

int main() {
    char buffer[10];
    char input[100];
    
    printf("Enter input: ");
    gets(input);  // Dangerous function
    strcpy(buffer, input);  // Potential buffer overflow
    
    printf("You entered: %s\n", input);
    return 0;
}