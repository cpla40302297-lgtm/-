"""
스케줄러 모듈 - 예약 게시물 관리
"""
import json
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, List, Optional


SCHEDULE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schedules.json")


class ScheduledPost:
    """예약 게시물 데이터 클래스"""
    
    def __init__(
        self,
        post_id: str,
        band_key: str,
        band_name: str,
        content: str,
        scheduled_time: datetime,
        do_push: bool = True,
        image_paths: List[str] = None,
        repeat: str = "none",  # none, daily, weekly
        status: str = "pending",  # pending, done, failed
    ):
        self.post_id = post_id
        self.band_key = band_key
        self.band_name = band_name
        self.content = content
        self.scheduled_time = scheduled_time
        self.do_push = do_push
        self.image_paths = image_paths or []
        self.repeat = repeat
        self.status = status
    
    def to_dict(self) -> dict:
        return {
            "post_id": self.post_id,
            "band_key": self.band_key,
            "band_name": self.band_name,
            "content": self.content,
            "scheduled_time": self.scheduled_time.strftime("%Y-%m-%d %H:%M:%S"),
            "do_push": self.do_push,
            "image_paths": self.image_paths,
            "repeat": self.repeat,
            "status": self.status,
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "ScheduledPost":
        return cls(
            post_id=d["post_id"],
            band_key=d["band_key"],
            band_name=d.get("band_name", ""),
            content=d["content"],
            scheduled_time=datetime.strptime(d["scheduled_time"], "%Y-%m-%d %H:%M:%S"),
            do_push=d.get("do_push", True),
            image_paths=d.get("image_paths", []),
            repeat=d.get("repeat", "none"),
            status=d.get("status", "pending"),
        )
    
    @property
    def is_due(self) -> bool:
        return self.status == "pending" and datetime.now() >= self.scheduled_time
    
    @property
    def time_until(self) -> str:
        if self.status != "pending":
            return self.status
        delta = self.scheduled_time - datetime.now()
        if delta.total_seconds() < 0:
            return "지금 즉시"
        hours, rem = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(rem, 60)
        if hours > 0:
            return f"{hours}시간 {minutes}분 후"
        elif minutes > 0:
            return f"{minutes}분 {seconds}초 후"
        else:
            return f"{seconds}초 후"


class Scheduler:
    """예약 게시물 스케줄러"""
    
    def __init__(self, schedule_file: str = SCHEDULE_FILE):
        self.schedule_file = schedule_file
        self.posts: List[ScheduledPost] = []
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._on_post_callback: Optional[Callable] = None
        self._on_update_callback: Optional[Callable] = None
        self._counter = 0
        self.load()
    
    def set_post_callback(self, cb: Callable):
        """게시 실행 콜백 (band_key, content, do_push, image_paths) -> bool"""
        self._on_post_callback = cb
    
    def set_update_callback(self, cb: Callable):
        """UI 업데이트 콜백"""
        self._on_update_callback = cb
    
    def _generate_id(self) -> str:
        self._counter += 1
        return f"post_{int(time.time())}_{self._counter}"
    
    def add_post(
        self,
        band_key: str,
        band_name: str,
        content: str,
        scheduled_time: datetime,
        do_push: bool = True,
        image_paths: List[str] = None,
        repeat: str = "none",
    ) -> ScheduledPost:
        """예약 게시물 추가"""
        post = ScheduledPost(
            post_id=self._generate_id(),
            band_key=band_key,
            band_name=band_name,
            content=content,
            scheduled_time=scheduled_time,
            do_push=do_push,
            image_paths=image_paths or [],
            repeat=repeat,
        )
        self.posts.append(post)
        self.save()
        return post
    
    def remove_post(self, post_id: str) -> bool:
        """예약 게시물 삭제"""
        before = len(self.posts)
        self.posts = [p for p in self.posts if p.post_id != post_id]
        if len(self.posts) < before:
            self.save()
            return True
        return False
    
    def get_pending_posts(self) -> List[ScheduledPost]:
        return [p for p in self.posts if p.status == "pending"]
    
    def get_all_posts(self) -> List[ScheduledPost]:
        return list(self.posts)
    
    def save(self):
        try:
            with open(self.schedule_file, "w", encoding="utf-8") as f:
                json.dump([p.to_dict() for p in self.posts], f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"스케줄 저장 오류: {e}")
    
    def load(self):
        if os.path.exists(self.schedule_file):
            try:
                with open(self.schedule_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.posts = [ScheduledPost.from_dict(d) for d in data]
            except (json.JSONDecodeError, IOError, KeyError):
                self.posts = []
    
    def start(self):
        """스케줄러 시작"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """스케줄러 중지"""
        self._running = False
    
    def _run_loop(self):
        """스케줄러 메인 루프 (30초 간격 체크)"""
        while self._running:
            self._check_and_execute()
            time.sleep(30)
    
    def _check_and_execute(self):
        """만료된 예약 게시물 실행"""
        changed = False
        for post in self.posts:
            if post.is_due and self._on_post_callback:
                try:
                    success = self._on_post_callback(
                        post.band_key,
                        post.content,
                        post.do_push,
                        post.image_paths,
                    )
                    if success:
                        post.status = "done"
                        # 반복 설정 처리
                        if post.repeat == "daily":
                            post.scheduled_time += timedelta(days=1)
                            post.status = "pending"
                        elif post.repeat == "weekly":
                            post.scheduled_time += timedelta(weeks=1)
                            post.status = "pending"
                    else:
                        post.status = "failed"
                    changed = True
                except Exception as e:
                    post.status = "failed"
                    print(f"예약 게시 실패 [{post.post_id}]: {e}")
                    changed = True
        
        if changed:
            self.save()
            if self._on_update_callback:
                self._on_update_callback()
