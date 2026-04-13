"""文件夹管理 REST API 端点，提供文件夹的增删改查及文件移动接口。"""
from flask import Blueprint, request
from Backend.Application.UseCases.FolderUseCase import FolderUseCase

folder_bp = Blueprint("folders", __name__, url_prefix="/api/folders")


def create_folder_blueprint(folder_use_case: FolderUseCase) -> Blueprint:

    @folder_bp.route("", methods=["POST"])
    def create_folder():
        data = request.get_json()
        if not data or not data.get("name"):
            return {"error": "Folder name is required"}, 400
        name = data["name"].strip()
        if not name:
            return {"error": "Folder name cannot be empty"}, 400
        try:
            folder = folder_use_case.create_folder(name)
            return folder.to_dict(), 201
        except ValueError as e:
            return {"error": str(e)}, 409

    @folder_bp.route("", methods=["GET"])
    def list_folders():
        folders = folder_use_case.list_folders()
        return folders

    @folder_bp.route("/<folder_id>", methods=["PATCH"])
    def rename_folder(folder_id: str):
        data = request.get_json()
        if not data or not data.get("name"):
            return {"error": "New folder name is required"}, 400
        new_name = data["name"].strip()
        if not new_name:
            return {"error": "Folder name cannot be empty"}, 400
        try:
            folder = folder_use_case.rename_folder(folder_id, new_name)
            return folder.to_dict(), 200
        except ValueError as e:
            return {"error": str(e)}, 404

    @folder_bp.route("/<folder_id>", methods=["DELETE"])
    def delete_folder(folder_id: str):
        try:
            folder_use_case.delete_folder(folder_id)
            return {"message": "Folder deleted"}, 200
        except ValueError as e:
            return {"error": str(e)}, 404

    @folder_bp.route("/<folder_id>/files", methods=["POST"])
    def move_file_to_folder(folder_id: str):
        data = request.get_json()
        if not data or not data.get("file_id"):
            return {"error": "file_id is required"}, 400
        try:
            folder_use_case.move_file_to_folder(data["file_id"], folder_id)
            return {"message": "File moved to folder"}, 200
        except ValueError as e:
            return {"error": str(e)}, 404

    @folder_bp.route("/unfile", methods=["POST"])
    def remove_file_from_folder():
        data = request.get_json()
        if not data or not data.get("file_id"):
            return {"error": "file_id is required"}, 400
        try:
            folder_use_case.move_file_to_folder(data["file_id"], None)
            return {"message": "File removed from folder"}, 200
        except ValueError as e:
            return {"error": str(e)}, 404

    return folder_bp
