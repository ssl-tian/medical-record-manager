# -*- coding: utf-8 -*-
"""
数据存储模块
负责患者数据的持久化、读取和索引维护
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime


class PatientStorage:
    """患者数据存储管理类"""

    def __init__(self, base_dir: str = None):
        """
        初始化存储管理器

        Args:
            base_dir: 基础目录路径，默认为当前工作目录
        """
        if base_dir is None:
            self.base_dir = Path.cwd()
        else:
            self.base_dir = Path(base_dir)

        self.patients_dir = self.base_dir / "patients"
        self.index_file = self.patients_dir / "patient_index.json"

        # 确保目录存在
        self._ensure_directories()

    def _ensure_directories(self):
        """确保存储目录存在"""
        self.patients_dir.mkdir(parents=True, exist_ok=True)

    def _get_patient_file_path(self, patient_id: str) -> Path:
        """
        获取患者数据文件路径

        Args:
            patient_id: 住院号

        Returns:
            患者数据文件的完整路径
        """
        return self.patients_dir / f"{patient_id}.json"

    def save_patient(self, patient_data: Dict) -> bool:
        """
        保存患者数据

        Args:
            patient_data: 患者数据字典

        Returns:
            保存是否成功
        """
        try:
            patient_id = patient_data.get("patient_id")
            if not patient_id:
                raise ValueError("患者数据中缺少patient_id字段")

            # 获取文件路径
            patient_file = self._get_patient_file_path(patient_id)

            # 原子写入：先写临时文件，再重命名
            temp_file = patient_file.with_suffix(".tmp")

            # 添加/更新元数据
            patient_data["metadata"] = {
                "created_at": patient_data.get("metadata", {}).get("created_at", datetime.now().isoformat()),
                "updated_at": datetime.now().isoformat()
            }

            # 写入临时文件
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(patient_data, f, ensure_ascii=False, indent=2)

            # 重命名为正式文件
            temp_file.replace(patient_file)

            # 更新索引
            self._update_index(patient_id, patient_data.get("basic_info", {}).get("name"))

            return True

        except Exception as e:
            print(f"[ERROR] 保存患者数据失败: {e}")
            return False

    def load_patient(self, patient_id: str) -> Optional[Dict]:
        """
        加载患者数据

        Args:
            patient_id: 住院号

        Returns:
            患者数据字典，不存在返回None
        """
        try:
            patient_file = self._get_patient_file_path(patient_id)

            if not patient_file.exists():
                return None

            with open(patient_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        except Exception as e:
            print(f"加载患者数据失败: {e}")
            return None

    def patient_exists(self, patient_id: str) -> bool:
        """
        检查患者是否存在

        Args:
            patient_id: 住院号

        Returns:
            是否存在
        """
        return self._get_patient_file_path(patient_id).exists()

    def list_all_patients(self) -> List[Dict]:
        """
        列出所有患者

        Returns:
            患者信息列表
        """
        try:
            patients = []

            for patient_file in self.patients_dir.glob("*.json"):
                if patient_file.name == "patient_index.json":
                    continue

                with open(patient_file, 'r', encoding='utf-8') as f:
                    patient_data = json.load(f)
                    patients.append({
                        "patient_id": patient_data.get("patient_id"),
                        "name": patient_data.get("basic_info", {}).get("name"),
                        "status": patient_data.get("status"),
                        "admission_date": patient_data.get("basic_info", {}).get("admission_date")
                    })

            return patients

        except Exception as e:
            print(f"列出患者失败: {e}")
            return []

    def _update_index(self, patient_id: str, patient_name: str):
        """
        更新患者索引

        Args:
            patient_id: 住院号
            patient_name: 患者姓名
        """
        try:
            # 读取现有索引
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    index = json.load(f)
            else:
                index = {}

            # 更新索引
            if patient_name:
                index[patient_name] = patient_id

            # 保存索引
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"更新索引失败: {e}")

    def get_patient_id_by_name(self, name: str) -> Optional[str]:
        """
        根据姓名获取住院号

        Args:
            name: 患者姓名

        Returns:
            住院号，不存在返回None
        """
        try:
            if not self.index_file.exists():
                return None

            with open(self.index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)

            return index.get(name)

        except Exception as e:
            print(f"查询索引失败: {e}")
            return None

    def delete_patient(self, patient_id: str) -> bool:
        """
        删除患者数据（谨慎使用）

        Args:
            patient_id: 住院号

        Returns:
            删除是否成功
        """
        try:
            patient_file = self._get_patient_file_path(patient_id)

            if not patient_file.exists():
                return False

            # 获取患者姓名以更新索引
            patient_data = self.load_patient(patient_id)
            patient_name = patient_data.get("basic_info", {}).get("name") if patient_data else None

            # 删除文件
            patient_file.unlink()

            # 更新索引
            if patient_name:
                self._remove_from_index(patient_name)

            return True

        except Exception as e:
            print(f"[ERROR] 删除患者数据失败: {e}")
            return False

    def _remove_from_index(self, patient_name: str):
        """
        从索引中移除患者

        Args:
            patient_name: 患者姓名
        """
        try:
            if not self.index_file.exists():
                return

            with open(self.index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)

            if patient_name in index:
                del index[patient_name]

            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"更新索引失败: {e}")
