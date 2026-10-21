/**
 * Superficial file checks for the upload control.
 * The filename, extension, and size are not proof the content is valid.
 * The server remains authoritative, including its 5 MiB limit.
 */
export const CLIENT_UPLOAD_BYTE_LIMIT = 5 * 1024 * 1024

export function clientFileNotice(file: File): string | null {
  if (!file.name.toLowerCase().endsWith(".csv")) {
    return "Choose a file whose name ends in .csv."
  }
  if (file.size > CLIENT_UPLOAD_BYTE_LIMIT) {
    return "This file is larger than 5 MiB."
  }
  return null
}
