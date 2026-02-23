"""
GUI 미리보기 테스트 (헤드리스 환경에서도 임포트 테스트)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """모듈 임포트 테스트"""
    from src.band_api import BandAPI, BandAPIError
    from src.config_manager import ConfigManager
    from src.scheduler import Scheduler, ScheduledPost
    print("✅ 모든 모듈 임포트 성공")

def test_config():
    """설정 관리 테스트"""
    from src.config_manager import ConfigManager
    import tempfile, os
    
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp = f.name
    
    try:
        cm = ConfigManager(tmp)
        cm.set("client_id", "test123")
        cm.add_template("공지", "공지사항 내용")
        cm.add_template("인사", "안녕하세요!")
        cm.save()
        
        # 다시 로드
        cm2 = ConfigManager(tmp)
        assert cm2.get("client_id") == "test123"
        assert len(cm2.get_templates()) == 2
        assert cm2.get_template_content("공지") == "공지사항 내용"
        
        cm2.delete_template("공지")
        assert len(cm2.get_templates()) == 1
        
        print("✅ ConfigManager 테스트 통과")
    finally:
        os.unlink(tmp)

def test_scheduler():
    """스케줄러 테스트"""
    from src.scheduler import Scheduler, ScheduledPost
    from datetime import datetime, timedelta
    import tempfile, os
    
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp = f.name
    
    try:
        sch = Scheduler(tmp)
        
        # 예약 추가
        t1 = datetime.now() + timedelta(hours=1)
        t2 = datetime.now() + timedelta(days=1)
        
        p1 = sch.add_post("band1", "밴드A", "내용1", t1, True, [], "none")
        p2 = sch.add_post("band2", "밴드B", "내용2", t2, False, [], "daily")
        
        assert len(sch.get_all_posts()) == 2
        assert len(sch.get_pending_posts()) == 2
        assert p1.time_until != "done"
        
        # 삭제
        sch.remove_post(p1.post_id)
        assert len(sch.get_all_posts()) == 1
        
        print("✅ Scheduler 테스트 통과")
    finally:
        os.unlink(tmp)

def test_band_api():
    """BandAPI 인스턴스 테스트"""
    from src.band_api import BandAPI, BandAPIError
    
    api = BandAPI("test_id", "test_secret")
    
    # 인증 URL 생성
    url = api.get_auth_url()
    assert "response_type=code" in url
    assert "test_id" in url
    
    # 미인증 상태
    assert not api.is_authenticated()
    
    # 토큰 설정
    api.set_access_token("fake_token_xyz")
    assert api.is_authenticated()
    
    # 미인증 시 에러
    api2 = BandAPI("x", "y")
    try:
        api2.get_bands()
        assert False, "예외가 발생해야 합니다"
    except BandAPIError as e:
        assert "액세스 토큰" in str(e)
    
    print("✅ BandAPI 테스트 통과")

if __name__ == "__main__":
    print("=" * 50)
    print("N Band Writer - 단위 테스트")
    print("=" * 50)
    
    tests = [test_imports, test_config, test_scheduler, test_band_api]
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} 실패: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print()
    print(f"결과: {passed}개 통과 / {failed}개 실패")
    
    if failed == 0:
        print("🎉 모든 테스트 통과!")
    else:
        sys.exit(1)
