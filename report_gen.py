import os
import requests
import json
import datetime


BASE_URL = "https://app.asana.com/api/1.0"


class AsanaAPI:
    def __init__(self):
        """Initialize Asana API with environment variables"""
        self.token = os.getenv("ASANA_ACCESS_TOKEN")
        self.section_id = os.getenv("ASANA_SECTION_ID")
        self.team_name = os.getenv("ASANA_TEAM_NAME", "Engagement")  # Default to "Engagement"
        self.priority_field = os.getenv("ASANA_PRIORITY_FIELD", "Priority")  # Default to "Priority"

        if not self.token:
            raise ValueError("ASANA_ACCESS_TOKEN is required in environment variables")
        if not self.section_id:
            raise ValueError("ASANA_SECTION_ID is required in environment variables")

        self.headers = {"Authorization": f"Bearer {self.token}"}

    def fetch_tasks_with_pagination(self, url):
        """Fetch tasks from Asana with pagination"""
        all_tasks = []

        while url:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                raise Exception(f"API request failed: {response.status_code}")

            data = response.json()
            tasks = data.get("data", [])

            # Filter tasks where Team == ASANA_TEAM_NAME
            for task in tasks:
                for field in task.get("custom_fields", []):
                    if field.get("name") == "Team" and field.get("display_value") == self.team_name:
                        all_tasks.append(task)
                        break

            # Handle pagination
            next_page = data.get("next_page")
            if next_page:
                url = f"{BASE_URL}/sections/{self.section_id}/tasks?opt_fields=custom_fields,created_at,completed,assignee.name&offset={next_page['offset']}"
            else:
                url = ""

        return all_tasks

    def get_pending_tasks(self):
        """Fetch the number of incomplete tasks in a section"""
        url = f"{BASE_URL}/sections/{self.section_id}/tasks?opt_fields=completed,custom_fields,assignee.name,created_at"
        tasks = self.fetch_tasks_with_pagination(url)
        return sum(1 for task in tasks if not task.get("completed", False))

    def get_incoming_tasks_grouped_by_priority(self):
        """Fetch tasks created this month and group them by Priority"""
        url = f"{BASE_URL}/sections/{self.section_id}/tasks?opt_fields=custom_fields,created_at"
        tasks = self.fetch_tasks_with_pagination(url)

        current_month = datetime.datetime.utcnow().strftime("%Y-%m")
        priority_counts = {}

        for task in tasks:
            created_at = task.get("created_at")
            if not created_at:
                continue

            task_date = datetime.datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%fZ")
            if task_date.strftime("%Y-%m") != current_month:
                continue

            for field in task.get("custom_fields", []):
                if field.get("name") == self.priority_field:
                    priority_counts[field.get("display_value", "Unknown")] = (
                            priority_counts.get(field.get("display_value", "Unknown"), 0) + 1
                    )

        return sorted(priority_counts.items(), key=lambda x: x[1], reverse=True)

    def get_tasks_grouped_by_priority(self):
        """Fetch tasks and group them by Priority (ONLY INCOMPLETE TASKS)"""
        url = f"{BASE_URL}/sections/{self.section_id}/tasks?opt_fields=custom_fields,completed"
        tasks = self.fetch_tasks_with_pagination(url)

        priority_counts = {}

        for task in tasks:
            if task.get("completed", False):
                continue

            for field in task.get("custom_fields", []):
                if field.get("name") == self.priority_field:
                    priority_counts[field.get("display_value", "Unknown")] = (
                            priority_counts.get(field.get("display_value", "Unknown"), 0) + 1
                    )

        return priority_counts

    def get_tasks_grouped_by_assignee(self):
        """Fetch tasks and group them by Assignee (ONLY INCOMPLETE TASKS)"""
        url = f"{BASE_URL}/sections/{self.section_id}/tasks?opt_fields=custom_fields,assignee.name,completed"
        tasks = self.fetch_tasks_with_pagination(url)

        assignee_counts = {}

        for task in tasks:
            if task.get("completed", False):
                continue

            assignee_name = task.get("assignee", {}).get("name", "Unassigned")
            assignee_counts[assignee_name] = assignee_counts.get(assignee_name, 0) + 1

        return sorted(assignee_counts.items(), key=lambda x: x[1], reverse=True)


def main():
    """Main function to execute the Asana API queries"""
    asana_api = AsanaAPI()

    # Get pending tasks
    try:
        pending_tasks = asana_api.get_pending_tasks()
        print(f"📌 Number of pending tasks in section: {pending_tasks}")
    except Exception as e:
        print(f"Error fetching pending tasks: {e}")

    # Get incoming tasks grouped by Priority
    try:
        incoming_priority_tasks = asana_api.get_incoming_tasks_grouped_by_priority()
        print("📥 Incoming Tasks grouped by Priority:")
        if not incoming_priority_tasks:
            print("   - 0")
        else:
            for priority, count in incoming_priority_tasks:
                print(f"   - {priority}: {count}")
    except Exception as e:
        print(f"Error fetching incoming tasks by priority: {e}")

    # Get tasks grouped by Priority
    try:
        priority_tasks = asana_api.get_tasks_grouped_by_priority()
        print("🔥 Tasks grouped by Priority:")
        for priority, count in priority_tasks.items():
            print(f"   - {priority}: {count}")
    except Exception as e:
        print(f"Error fetching tasks by priority: {e}")

    # Get tasks grouped by Assignee
    try:
        assignee_tasks = asana_api.get_tasks_grouped_by_assignee()
        print("👥 Tasks grouped by Assignee:")
        for assignee, count in assignee_tasks:
            print(f"   - {assignee}: {count}")
    except Exception as e:
        print(f"Error fetching tasks by assignee: {e}")


if __name__ == "__main__":
    main()
