#!/usr/bin/env python3
"""
N Band Writer - 네이버 밴드 자동 게시물 작성 프로그램
실행 진입점
"""
import sys
import os

# 실행 경로 설정
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app import main

if __name__ == "__main__":
    main()
