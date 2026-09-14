/**
 * G-2 mock. 실제 연계 API가 오면 이 목록만 갈아끼운다.
 */
import type { LocalResource } from "../types/contract";

export const DASAN_DEUNGBON_RESOURCES: readonly LocalResource[] = [
  {
    orgName: "서울출입국·외국인청",
    address: "서울 양천구 목동동로 151 · 서울 관할",
    phone: "1348",
  },
  {
    orgName: "종로구청 민원여권과",
    address: "서울 종로구 종로1길 36 · 등본·인감 창구",
    phone: "02-2148-1114",
  },
  {
    orgName: "중구 신당동 주민센터",
    address: "서울 중구 다산로 47 · 방문 발급",
    phone: "02-3396-5500",
  },
];

export const DEFAULT_LOCAL_RESOURCES: readonly LocalResource[] = [
  DASAN_DEUNGBON_RESOURCES[0],
  DASAN_DEUNGBON_RESOURCES[1],
];
