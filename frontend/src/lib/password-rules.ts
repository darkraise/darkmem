/** The server's password bounds (`app/schemas` validators), checked before
 *  submit so a form never walks the operator to a refusal it could have
 *  named up front.
 *
 *  The ceiling is bytes, not characters: bcrypt reads at most 72 bytes of
 *  UTF-8, so an accented or non-Latin password reaches it in fewer than 72
 *  characters. */
export const PASSWORD_MIN_CHARS = 8
export const PASSWORD_MAX_BYTES = 72

export function passwordBytes(value: string): number {
  return new TextEncoder().encode(value).length
}

export function passwordTooLong(value: string): boolean {
  return passwordBytes(value) > PASSWORD_MAX_BYTES
}
