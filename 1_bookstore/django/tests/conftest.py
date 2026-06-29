"""Django 통합 테스트용 설정.

이 예제는 gRPC 서버를 띄울 필요가 없다(주제가 protobuf 직렬화 그 자체).
pytest-django 가 settings 를 로드하도록 pyproject 의 DJANGO_SETTINGS_MODULE
설정만으로 충분하므로, 별도 픽스처는 두지 않는다.
"""
