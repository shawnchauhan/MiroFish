"""
Project context management
Persists project state on the server to avoid passing large data between API calls on the frontend
"""

import os
import json
import uuid
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field, asdict
from ..config import Config


class ProjectStatus(str, Enum):
    """Project status"""
    CREATED = "created"              # Just created, files uploaded
    ONTOLOGY_GENERATED = "ontology_generated"  # Ontology generated
    GRAPH_BUILDING = "graph_building"    # Graph building in progress
    GRAPH_COMPLETED = "graph_completed"  # Graph build complete
    FAILED = "failed"                # Failed


@dataclass
class Project:
    """Project data model"""
    project_id: str
    name: str
    status: ProjectStatus
    created_at: str
    updated_at: str
    
    # File information
    files: List[Dict[str, str]] = field(default_factory=list)  # [{filename, path, size}]
    total_text_length: int = 0
    
    # Ontology information (populated after endpoint 1 generates it)
    ontology: Optional[Dict[str, Any]] = None
    analysis_summary: Optional[str] = None
    
    # Graph information (populated after endpoint 2 completes)
    graph_id: Optional[str] = None
    graph_build_task_id: Optional[str] = None
    
    # Configuration
    simulation_requirement: Optional[str] = None
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    # Error information
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "project_id": self.project_id,
            "name": self.name,
            "status": self.status.value if isinstance(self.status, ProjectStatus) else self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "files": self.files,
            "total_text_length": self.total_text_length,
            "ontology": self.ontology,
            "analysis_summary": self.analysis_summary,
            "graph_id": self.graph_id,
            "graph_build_task_id": self.graph_build_task_id,
            "simulation_requirement": self.simulation_requirement,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Create from dictionary"""
        status = data.get('status', 'created')
        if isinstance(status, str):
            status = ProjectStatus(status)
        
        return cls(
            project_id=data['project_id'],
            name=data.get('name', 'Unnamed Project'),
            status=status,
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', ''),
            files=data.get('files', []),
            total_text_length=data.get('total_text_length', 0),
            ontology=data.get('ontology'),
            analysis_summary=data.get('analysis_summary'),
            graph_id=data.get('graph_id'),
            graph_build_task_id=data.get('graph_build_task_id'),
            simulation_requirement=data.get('simulation_requirement'),
            chunk_size=data.get('chunk_size', 500),
            chunk_overlap=data.get('chunk_overlap', 50),
            error=data.get('error')
        )


class ProjectManager:
    """Project manager - handles persistent storage and retrieval of projects

    All path methods require a ``user_id`` to scope storage under
    ``uploads/{user_id}/projects/``.
    """

    # Legacy class-level dir kept for reference; callers must use
    # the user-scoped helpers below.
    _LEGACY_PROJECTS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'projects')

    @staticmethod
    def _projects_dir(user_id: str) -> str:
        from ..utils.paths import user_projects_dir
        return user_projects_dir(user_id)

    @classmethod
    def _ensure_projects_dir(cls, user_id: str):
        """Ensure the projects directory exists"""
        os.makedirs(cls._projects_dir(user_id), exist_ok=True)

    @classmethod
    def _get_project_dir(cls, user_id: str, project_id: str) -> str:
        """Get project directory path"""
        return os.path.join(cls._projects_dir(user_id), project_id)

    @classmethod
    def _get_project_meta_path(cls, user_id: str, project_id: str) -> str:
        """Get project metadata file path"""
        return os.path.join(cls._get_project_dir(user_id, project_id), 'project.json')

    @classmethod
    def _get_project_files_dir(cls, user_id: str, project_id: str) -> str:
        """Get project file storage directory"""
        return os.path.join(cls._get_project_dir(user_id, project_id), 'files')

    @classmethod
    def _get_project_text_path(cls, user_id: str, project_id: str) -> str:
        """Get project extracted text storage path"""
        return os.path.join(cls._get_project_dir(user_id, project_id), 'extracted_text.txt')

    @classmethod
    def create_project(cls, user_id: str, name: str = "Unnamed Project") -> Project:
        """Create a new project"""
        cls._ensure_projects_dir(user_id)

        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        project = Project(
            project_id=project_id,
            name=name,
            status=ProjectStatus.CREATED,
            created_at=now,
            updated_at=now
        )

        # Create project directory structure
        project_dir = cls._get_project_dir(user_id, project_id)
        files_dir = cls._get_project_files_dir(user_id, project_id)
        os.makedirs(project_dir, exist_ok=True)
        os.makedirs(files_dir, exist_ok=True)

        # Save project metadata
        cls.save_project(user_id, project)

        return project

    @classmethod
    def save_project(cls, user_id: str, project: Project) -> None:
        """Save project metadata"""
        project.updated_at = datetime.now().isoformat()
        meta_path = cls._get_project_meta_path(user_id, project.project_id)

        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(project.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def get_project(cls, user_id: str, project_id: str) -> Optional[Project]:
        """Get a project"""
        meta_path = cls._get_project_meta_path(user_id, project_id)

        if not os.path.exists(meta_path):
            return None

        with open(meta_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return Project.from_dict(data)

    @classmethod
    def list_projects(cls, user_id: str, limit: int = 50) -> List[Project]:
        """List all projects for a user, sorted by creation time descending"""
        cls._ensure_projects_dir(user_id)

        projects_dir = cls._projects_dir(user_id)
        projects = []
        for project_id in os.listdir(projects_dir):
            project = cls.get_project(user_id, project_id)
            if project:
                projects.append(project)

        projects.sort(key=lambda p: p.created_at, reverse=True)
        return projects[:limit]

    @classmethod
    def find_project_by_graph_id(cls, user_id: str, graph_id: str) -> Optional[Project]:
        """Find a project owned by *user_id* that has the given *graph_id*.

        Returns the project if found, otherwise None.  Used to verify that
        the caller actually owns the graph before operating on it.
        """
        projects_dir = cls._projects_dir(user_id)
        if not os.path.isdir(projects_dir):
            return None
        for project_id in os.listdir(projects_dir):
            project = cls.get_project(user_id, project_id)
            if project and project.graph_id == graph_id:
                return project
        return None

    @classmethod
    def delete_project(cls, user_id: str, project_id: str) -> bool:
        """Delete a project and all its files"""
        project_dir = cls._get_project_dir(user_id, project_id)

        if not os.path.exists(project_dir):
            return False

        shutil.rmtree(project_dir)
        return True

    @classmethod
    def save_file_to_project(cls, user_id: str, project_id: str,
                             file_storage, original_filename: str) -> Dict[str, str]:
        """Save an uploaded file to the project directory"""
        files_dir = cls._get_project_files_dir(user_id, project_id)
        os.makedirs(files_dir, exist_ok=True)

        ext = os.path.splitext(original_filename)[1].lower()
        safe_filename = f"{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join(files_dir, safe_filename)

        file_storage.save(file_path)
        file_size = os.path.getsize(file_path)

        return {
            "original_filename": original_filename,
            "saved_filename": safe_filename,
            "path": file_path,
            "size": file_size
        }

    @classmethod
    def save_extracted_text(cls, user_id: str, project_id: str, text: str) -> None:
        """Save extracted text"""
        text_path = cls._get_project_text_path(user_id, project_id)
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text)

    @classmethod
    def get_extracted_text(cls, user_id: str, project_id: str) -> Optional[str]:
        """Get extracted text"""
        text_path = cls._get_project_text_path(user_id, project_id)

        if not os.path.exists(text_path):
            return None

        with open(text_path, 'r', encoding='utf-8') as f:
            return f.read()

    @classmethod
    def get_project_files(cls, user_id: str, project_id: str) -> List[str]:
        """Get all file paths for a project"""
        files_dir = cls._get_project_files_dir(user_id, project_id)

        if not os.path.exists(files_dir):
            return []

        return [
            os.path.join(files_dir, f)
            for f in os.listdir(files_dir)
            if os.path.isfile(os.path.join(files_dir, f))
        ]

