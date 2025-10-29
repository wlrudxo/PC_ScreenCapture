"""
활동 정보 → 태그 자동 분류 룰 엔진
"""
from fnmatch import fnmatch
from typing import Dict, Any, Optional, Tuple, List


class RuleEngine:
    """
    활동 정보 → 태그 자동 분류

    룰 우선순위 기반으로 매칭
    """

    def __init__(self, db_manager):
        """
        룰 엔진 초기화

        Args:
            db_manager: DatabaseManager 인스턴스
        """
        self.db_manager = db_manager
        self.rules_cache: List[Dict[str, Any]] = []
        self.reload_rules()

    def reload_rules(self):
        """DB에서 룰 불러오기 (우선순위 정렬)"""
        self.rules_cache = self.db_manager.get_all_rules(
            enabled_only=True,
            order_by='priority DESC'
        )
        print(f"[RuleEngine] {len(self.rules_cache)}개 룰 로드됨")

    def match(self, activity_info: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
        """
        활동 정보와 룰을 매칭해서 tag_id, rule_id 반환

        단순화된 로직:
        - 모든 상태(__LOCKED__, __IDLE__ 포함)를 통일된 방식으로 처리
        - priority 높은 룰부터 순회하며 첫 매칭 반환

        Args:
            activity_info: {
                'process_name': str,
                'window_title': str,
                'chrome_url': str,
                'chrome_profile': str
            }

        Returns:
            (tag_id, rule_id) 튜플
            매칭 실패 시 ('미분류' 태그 ID, None)
        """
        # 디버깅: 활동 정보 출력
        if activity_info.get('chrome_url'):
            print(f"[RuleEngine] 매칭 시도 - URL: {activity_info['chrome_url']}")

        # 룰 순회 (우선순위 높은 것부터)
        for rule in self.rules_cache:
            if self._is_matched(rule, activity_info):
                print(f"[RuleEngine] 매칭 성공 - 룰: {rule['name']}, 태그: {rule.get('tag_name', 'N/A')}")
                return rule['tag_id'], rule['id']

        # 매칭 실패 → "미분류" 태그
        print(f"[RuleEngine] 매칭 실패 - 미분류로 분류")
        unclassified_tag = self.db_manager.get_tag_by_name('미분류')
        if unclassified_tag:
            return unclassified_tag['id'], None
        else:
            # 미분류 태그가 없으면 자동 생성
            print("[RuleEngine] 경고: '미분류' 태그가 없어 자동 생성")
            tag_id = self.db_manager.create_tag('미분류', '#607D8B')
            return tag_id, None

    def _is_matched(self, rule: Dict[str, Any], activity_info: Dict[str, Any]) -> bool:
        """
        룰 조건과 활동 정보 매칭 (OR 관계)

        Args:
            rule: 룰 딕셔너리 (process_pattern, url_pattern, etc.)
            activity_info: 활동 정보 딕셔너리

        Returns:
            True: 매칭됨
            False: 매칭 안됨
        """
        # 프로세스 이름 매칭 (쉼표로 구분된 여러 패턴 지원)
        if rule.get('process_pattern'):
            process_name = activity_info.get('process_name', '')
            if process_name:
                # 쉼표로 구분된 패턴들을 각각 테스트
                patterns = [p.strip() for p in rule['process_pattern'].split(',')]
                for pattern in patterns:
                    if pattern and fnmatch(process_name, pattern):
                        return True

        # URL 패턴 매칭 (쉼표로 구분된 여러 패턴 지원)
        if rule.get('url_pattern'):
            chrome_url = activity_info.get('chrome_url', '')
            if chrome_url:
                # 쉼표로 구분된 패턴들을 각각 테스트
                patterns = [p.strip() for p in rule['url_pattern'].split(',')]
                for pattern in patterns:
                    if pattern and fnmatch(chrome_url, pattern):
                        return True

        # Chrome 프로필 매칭
        if rule.get('chrome_profile'):
            chrome_profile = activity_info.get('chrome_profile', '')
            if chrome_profile and chrome_profile == rule['chrome_profile']:
                return True

        # 창 제목 매칭 (쉼표로 구분된 여러 패턴 지원)
        if rule.get('window_title_pattern'):
            window_title = activity_info.get('window_title', '')
            if window_title:
                # 쉼표로 구분된 패턴들을 각각 테스트
                patterns = [p.strip() for p in rule['window_title_pattern'].split(',')]
                for pattern in patterns:
                    if pattern and fnmatch(window_title, pattern):
                        return True

        return False
