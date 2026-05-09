import { createCipheriv, createDecipheriv, randomBytes } from "crypto";
import { AppError } from "./errors";

const ALGORITHM = "aes-256-gcm";
const IV_LENGTH = 12;
const AUTH_TAG_LENGTH = 16;

function getEncryptionKey(): Buffer {
  const key = process.env.AI_KEY_ENCRYPTION_SECRET;
  if (!key) {
    throw new AppError("AI 密钥加密服务未配置，请联系管理员", "blocking", "CONFIG_MISSING", 500);
  }
  return Buffer.from(key, "hex");
}

/**
 * 加密 API Key
 * 存储格式: base64(iv + ciphertext + authTag)
 */
export function encryptApiKey(plainKey: string): string {
  const key = getEncryptionKey();
  const iv = randomBytes(IV_LENGTH);
  const cipher = createCipheriv(ALGORITHM, key, iv);

  const encrypted = Buffer.concat([cipher.update(plainKey, "utf8"), cipher.final()]);
  const authTag = cipher.getAuthTag();

  // iv (12) + encrypted (variable) + authTag (16)
  const combined = Buffer.concat([iv, encrypted, authTag]);
  return combined.toString("base64");
}

/**
 * 解密 API Key
 */
export function decryptApiKey(encryptedKey: string): string {
  const key = getEncryptionKey();
  const combined = Buffer.from(encryptedKey, "base64");

  const iv = combined.subarray(0, IV_LENGTH);
  const authTag = combined.subarray(combined.length - AUTH_TAG_LENGTH);
  const ciphertext = combined.subarray(IV_LENGTH, combined.length - AUTH_TAG_LENGTH);

  const decipher = createDecipheriv(ALGORITHM, key, iv);
  decipher.setAuthTag(authTag);

  const decrypted = Buffer.concat([decipher.update(ciphertext), decipher.final()]);

  return decrypted.toString("utf8");
}
