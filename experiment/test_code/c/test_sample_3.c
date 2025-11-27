#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_TITLE_LENGTH 128
#define MAX_TASKS 1000
#define FILENAME "tasks.txt"

typedef struct {
  char title[MAX_TITLE_LENGTH];
  int completed;
} Task;

Task tasks[MAX_TASKS];
int task_count = 0;

void trim_newline(char *str) {
  size_t len = strlen(str);
  if (len > 0 && str[len - 1] == '\n') {
    str[len - 1] = '\0';
  }
}

void load_tasks() {
  FILE *file = fopen(FILENAME, "r");
  if (!file) {
    printf("No saved tasks found. Starting fresh.\n");
    return;
  }

  char line[256];
  while (fgets(line, sizeof(line), file)) {
    if (task_count >= MAX_TASKS) {
      printf("Warning: Max tasks (%d) reached. Skipping extra tasks.\n",
             MAX_TASKS);
      break;
    }
    trim_newline(line);
    if (strlen(line) < 3)
      continue;

    char status_char = line[0];
    if (status_char != '0' && status_char != '1')
      continue;

    tasks[task_count].completed = (status_char == '1');
    strncpy(tasks[task_count].title, line + 2, MAX_TITLE_LENGTH - 1);
    tasks[task_count].title[MAX_TITLE_LENGTH - 1] = '\0';
    task_count++;
  }

  fclose(file);
  printf("Loaded %d tasks from %s.\n", task_count, FILENAME);
}

void save_tasks() {
  FILE *file = fopen(FILENAME, "w");
  if (!file) {
    perror("Failed to open file for saving");
    return;
  }

  for (int i = 0; i < task_count; i++) {
    fprintf(file, "%c %s\n", tasks[i].completed ? '1' : '0', tasks[i].title);
  }

  fclose(file);
  printf("Tasks saved to %s.\n", FILENAME);
}

void add_task() {
  if (task_count >= MAX_TASKS) {
    printf("Task list is full! (Max: %d)\n", MAX_TASKS);
    return;
  }

  printf("Enter task title (max %d chars): ", MAX_TITLE_LENGTH - 1);
  char input[MAX_TITLE_LENGTH * 2];
  if (!fgets(input, sizeof(input), stdin)) {
    printf("Input error.\n");
    return;
  }
  trim_newline(input);

  if (strlen(input) == 0) {
    printf("Task title cannot be empty.\n");
    return;
  }

  strncpy(tasks[task_count].title, input, MAX_TITLE_LENGTH - 1);
  tasks[task_count].title[MAX_TITLE_LENGTH - 1] = '\0';
  tasks[task_count].completed = 0;
  task_count++;
  printf("Task added: \"%s\"\n", input);
}

void list_tasks() {
  if (task_count == 0) {
    printf("No tasks to display.\n");
    return;
  }

  printf("\n--- TASK LIST ---\n");
  for (int i = 0; i < task_count; i++) {
    char status = tasks[i].completed ? 'v' : 'o';
    printf("%3d. [%c] %s\n", i + 1, status, tasks[i].title);
  }
  printf("-----------------\n");
}

void complete_task() {
  if (task_count == 0) {
    printf("No tasks available to complete.\n");
    return;
  }

  list_tasks();
  printf("Enter task number to mark as completed (0 to cancel): ");
  int num;
  if (scanf("%d", &num) != 1) {
    printf("Invalid input.\n");
    while (getchar() != '\n')
      ; // clear input buffer
    return;
  }

  if (num == 0) {
    printf("Operation cancelled.\n");
    return;
  }

  if (num < 1 || num > task_count) {
    printf("Invalid task number.\n");
    return;
  }

  if (tasks[num - 1].completed) {
    printf("Task already completed!\n");
  } else {
    tasks[num - 1].completed = 1;
    printf("Task \"%s\" marked as completed.\n", tasks[num - 1].title);
  }

  while (getchar() != '\n')
    ; // consume leftover newline
}

void delete_task() {
  if (task_count == 0) {
    printf("No tasks to delete.\n");
    return;
  }

  list_tasks();
  printf("Enter task number to delete (0 to cancel): ");
  int num;
  if (scanf("%d", &num) != 1) {
    printf("Invalid input.\n");
    while (getchar() != '\n')
      ;
    return;
  }

  if (num == 0) {
    printf("Operation cancelled.\n");
    return;
  }

  if (num < 1 || num > task_count) {
    printf("Invalid task number.\n");
    return;
  }

  // Shift all tasks after this one
  for (int i = num - 1; i < task_count - 1; i++) {
    tasks[i] = tasks[i + 1];
  }
  task_count--;
  printf("Task deleted.\n");

  while (getchar() != '\n')
    ;
}

void print_menu() {
  printf("\n===== TASK MANAGER =====\n");
  printf("1. Add Task\n");
  printf("2. List Tasks\n");
  printf("3. Complete Task\n");
  printf("4. Delete Task\n");
  printf("5. Save Tasks\n");
  printf("6. Exit\n");
  printf("========================\n");
  printf("Choose an option: ");
}

int main() {
  load_tasks();

  int choice;
  while (1) {
    print_menu();
    if (scanf("%d", &choice) != 1) {
      printf("Invalid input. Please enter a number.\n");
      while (getchar() != '\n')
        ; // clear buffer
      continue;
    }

    while (getchar() != '\n')
      ; // consume newline after number

    switch (choice) {
    case 1:
      add_task();
      break;
    case 2:
      list_tasks();
      break;
    case 3:
      complete_task();
      break;
    case 4:
      delete_task();
      break;
    case 5:
      save_tasks();
      break;
    case 6:
      save_tasks();
      printf("Goodbye!\n");
      return 0;
    default:
      printf("Invalid option. Please try again.\n");
    }
  }

  return 0;
}
