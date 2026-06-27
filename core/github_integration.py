import logging
import requests
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class GitHubIntegration:
    """
    Manages GitHub API integration for issue creation
    """
    
    def __init__(self, token: str, owner: str, repo: str):
        """
        Initialize GitHub integration
        
        Args:
            token: GitHub personal access token
            owner: Repository owner username
            repo: Repository name
        """
        self.token = token
        self.owner = owner
        self.repo = repo
        self.base_url = "https://api.github.com"
        logger.info(f"GitHubIntegration initialized for {owner}/{repo}")
    
    def create_issue(self, title: str, body: str, labels: List[str] = None) -> Tuple[bool, str]:
        """
        Create a GitHub issue
        
        Args:
            title: Issue title
            body: Issue body/description
            labels: Optional list of labels
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues"
        
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json"
        }
        
        data = {
            "title": title,
            "body": body
        }
        
        if labels:
            data["labels"] = labels
        
        try:
            logger.info(f"Creating GitHub issue: {title}")
            response = requests.post(url, headers=headers, json=data, timeout=20)
            
            if response.status_code == 201:
                issue_url = response.json().get("html_url", "")
                logger.info(f"Issue created successfully: {issue_url}")
                return True, issue_url
            else:
                error_msg = f"Failed to create issue. Status: {response.status_code}"
                logger.error(error_msg)
                return False, error_msg
        
        except requests.exceptions.Timeout:
            error_msg = "Request timed out"
            logger.error(error_msg)
            return False, error_msg
        
        except Exception as e:
            error_msg = f"Error creating issue: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def create_issues_from_tasks(self, tasks: List[Dict]) -> Dict[str, int]:
        """
        Create multiple GitHub issues from task list
        
        Args:
            tasks: List of task dictionaries
        
        Returns:
            Dictionary with success and failure counts
        """
        results = {"success": 0, "failed": 0, "failed_tasks": []}
        
        for task in tasks:
            title = task.get("Task Title", "Untitled Task")
            
            body = f"""
### Task Summary
{task.get('Summary', 'No description provided')}

### Priority
{task.get('Priority', 'Medium')}

### Type
{task.get('Type', 'General')}

### Full Description
{task.get('Full Task', 'No additional details')}

---
*Created by Meet2Task AI*
"""
            
            # Determine labels based on priority and type
            labels = []
            priority = task.get('Priority', 'Medium').lower()
            task_type = task.get('Type', 'General').lower()
            
            if priority == 'high':
                labels.append('priority: high')
            elif priority == 'low':
                labels.append('priority: low')
            
            if task_type in ['bug', 'feature', 'documentation']:
                labels.append(task_type)
            
            success, message = self.create_issue(title, body, labels)
            
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
                results["failed_tasks"].append(title)
        
        logger.info(f"GitHub issue creation complete. Success: {results['success']}, Failed: {results['failed']}")
        return results
    
    def validate_credentials(self) -> Tuple[bool, str]:
        """
        Validate GitHub credentials
        
        Returns:
            Tuple of (valid: bool, message: str)
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}"
        headers = {"Authorization": f"token {self.token}"}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info("GitHub credentials validated successfully")
                return True, "Credentials valid"
            elif response.status_code == 404:
                return False, "Repository not found"
            elif response.status_code == 401:
                return False, "Invalid token"
            else:
                return False, f"Validation failed: {response.status_code}"
        
        except Exception as e:
            logger.error(f"Credential validation failed: {e}")
            return False, str(e)