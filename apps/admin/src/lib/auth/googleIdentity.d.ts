/** Google Identity Services 전역 객체 — 쓰는 만큼만 타입을 둔다 (index.html의 gsi/client 스크립트가 채운다). */
interface GoogleIdCredentialResponse {
  credential: string; // id_token(JWT)
}

interface GoogleAccountsId {
  initialize(config: {
    client_id: string;
    callback: (response: GoogleIdCredentialResponse) => void;
  }): void;
  renderButton(
    parent: HTMLElement,
    options: { theme?: "outline" | "filled_blue" | "filled_black"; size?: "small" | "medium" | "large"; text?: string; width?: number },
  ): void;
}

interface Window {
  google?: {
    accounts: {
      id: GoogleAccountsId;
    };
  };
}
