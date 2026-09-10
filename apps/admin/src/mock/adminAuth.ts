/** 관리자 표시 이름. 계정 API가 오면 이 값만 서버 응답으로 바꾼다. */
export interface MockAdminAccount {
  name: string;
}

const account: MockAdminAccount = {
  name: "관리자",
};

export function getMockAdminAccount(): MockAdminAccount {
  return { ...account };
}
