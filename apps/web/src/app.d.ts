declare global {
  namespace App {
    interface Locals {
      user: {
        subject: string;
        name: string;
        email?: string;
        roles: string[];
      } | null;
    }
  }
}

export {};
