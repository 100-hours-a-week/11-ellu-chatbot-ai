## [1.0.1](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/compare/v1.0.0...v1.0.1) (2025-07-19)


### Bug Fixes

* ASSISTANT 중복 저장 수정 ([#93](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/93)) ([#94](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/94)) ([10fff9b](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/10fff9b4148efd13230dc3b36101dfcf22da9a0b))
* chat/query API 엔드포인트 수정 ([#89](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/89)) ([#90](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/90)) ([e686519](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/e686519df49e593b2078d3299fc59849e090fece))
* fetch_schedule 무한 호출 오류 수정 ([#91](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/91)) ([#92](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/92)) ([4b3ce31](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/4b3ce31b4bf76274bb0cfc3d21080266eb3fd3bd))

# 1.0.0 (2025-07-08)


### Bug Fixes

* await 없는 async function ([fccee7d](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/fccee7ddce87af92bdd04cc839fb662d5ab428bf))
* await 없는 async function ([8c2b51c](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/8c2b51c3a907fa24fc3ecce593c6b3e359c2a64d))
* langchain_tavily 패키지 설치 및 클래스명 수정 ([#35](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/35)) ([#36](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/36)) ([28b095c](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/28b095c1c7f7aa0b2535dafc47b51228ec5f5a68))
* preview 삭제 ([#50](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/50)) ([#51](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/51)) ([98907ce](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/98907ce557e9a4c08d67840488db0c4e6cda6c9d))
* recommend 추출 시에만 노드 넘어가도록 수정 ([#66](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/66)) ([#67](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/67)) ([e4a94a8](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/e4a94a8d487c8cf87e8b15225e935da6d2e5f88f))
* user_id int 타입 변환 ([#61](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/61)) ([#62](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/62)) ([11975af](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/11975aff060da7a4396aaa9816e254960b67d7ad))
* user_id str타입으로 수정 ([#54](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/54)) ([#55](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/55)) ([bec0be2](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/bec0be23f551c5f1d1c1e2ca86ba39749ff8c3fb))
* 일정 생성 완료 스트리밍 응답 done = True로 수정 ([#39](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/39)) ([#40](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/40)) ([2e9c24f](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/2e9c24f13e2b7a28649cd9f77021da07c8ce77bc))
* 재응답시 slot 추출 및 병합 수정 ([#31](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/31)) ([#32](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/32)) ([59c6712](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/59c6712784445af43a7c3f7c659ec7456c579fc6))


### Features

* add issue template ([#1](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/1)) ([2be15ee](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/2be15eef153c39e5d6eb96e2da40b9f4d415bb21))
* add issue template ([#1](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/1)) ([fedfbde](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/fedfbdead66e67b8161673428310c0a7d74dee84))
* chat 히스토리 postgreSQL db 저장 ([1b669f9](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/1b669f9d218c7e74117c96815f536253a9387de0))
* chat 히스토리 postgreSQL db 저장 ([41fcb50](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/41fcb5026b0acdf58a95645a39d67d15d46b0569))
* json output parser 구현 ([#10](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/10)) ([#13](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/13)) ([cf6c2d8](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/cf6c2d8cdd8695322b8a344ca8aa4b3ae0b80acf))
* json output parser 구현 ([#10](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/10)) ([#13](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/13)) ([6830ec2](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/6830ec281929ff8ca63fc50931490cba3be04a56))
* OpenAI model 설정 ([#2](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/2)) ([#3](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/3)) ([e073ce2](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/e073ce225830a8f5fdd7582c6660b0304fc156c9))
* OpenAI model 설정 ([#2](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/2)) ([#3](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/3)) ([c91d454](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/c91d4546cb2876b21d51b1f31c6d6fd2cebe1135))
* OpenTelemetry 트레이싱 패키지 추가 ([fba1e56](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/fba1e564cce5a2be65b5b51d90cd1327ecb4c1bd))
* OpenTelemetry 트레이싱 패키지 추가 ([502babf](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/502babf3a2dfb805a1359d9faace1b87e706fb1f))
* Prometheus 엔드포인트 추가 ([621a34c](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/621a34ca8ba7ef4df89e1add70feaeef197808a9))
* Prometheus 엔드포인트 추가 ([6134326](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/6134326cbaaa8e790b5467f276e7fa38ddae6a77))
* 목적별 프롬프트 구현 ([#11](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/11)) ([#12](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/12)) ([166c730](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/166c7307c022aa5a18ac284c27416e52c0a082b4))
* 목적별 프롬프트 구현 ([#11](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/11)) ([#12](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/12)) ([c9fa70d](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/c9fa70d1aa334c28c7319c39e294e929155baf7e))
* 사용자 히스토리 및 챗봇 응답 흐름 관리 ([#15](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/15)) ([#17](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/17)) ([fa2854d](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/fa2854d2898d15299fe771b492206ea10c30f236))
* 사용자 히스토리 및 챗봇 응답 흐름 관리 ([#15](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/15)) ([#17](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/17)) ([c6d39e8](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/c6d39e8aea91240251ccaf7763ade40e660d369a))
* 실시간 챗봇 응답 스트리밍 핸들러 기능 ([#16](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/16)) ([#18](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/18)) ([0d4acef](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/0d4acef5621261663a45322517bc7c7a64624f54))
* 실시간 챗봇 응답 스트리밍 핸들러 기능 ([#16](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/16)) ([#18](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/18)) ([fca274a](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/fca274ab044ee66e3a42d4db03f854cb6f86ffa0))
* 챗봇 스트리밍 컨트롤러 ([#19](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/19)) ([#22](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/22)) ([c4b3470](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/c4b347008f877d4f43bcead6f0e93a52595fac4b))
* 챗봇 스트리밍 컨트롤러 ([#19](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/19)) ([#22](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/22)) ([d59356a](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/d59356ae3092a7cb105514c224529287dedea621))
* 챗봇 유저 히스토리 저장 ([#14](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/14)) ([#21](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/21)) ([6ce78bd](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/6ce78bdb9d04ebd4ce2ba45e5cb63327cafbfd6e))
* 챗봇 유저 히스토리 저장 ([#14](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/14)) ([#21](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/21)) ([9cd0f31](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/9cd0f31b44c2dd4f0edb831b64ecd69a67d07a9c))
* 챗봇 응답별 chain 구현 ([#6](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/6)) ([#7](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/7)) ([7c95c2e](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/7c95c2ef76d021c36db30c180845efca639f8aff))
* 챗봇 응답별 chain 구현 ([#6](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/6)) ([#7](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/issues/7)) ([8107a78](https://github.com/100-hours-a-week/11-ellu-chatbot-ai/commit/8107a78d552e22d4b9c5fd7722d7236a3808d6d7))
