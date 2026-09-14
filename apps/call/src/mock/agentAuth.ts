/** 상담원 표시 이름. 계정 API가 오면 이 값만 서버 응답으로 바꾼다. */
export interface MockAgentAccount {
  name: string;
}

const account: MockAgentAccount = {
  name: "조서희",
};

export function getMockAgentAccount(): MockAgentAccount {
  return { ...account };
}
