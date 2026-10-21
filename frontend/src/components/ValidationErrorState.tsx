import styles from "./ValidationErrorState.module.css"

export function ValidationErrorState({ code, message }: { code: string; message: string }) {
  return (
    <section className={styles.panel} role="alert">
      <h1 className={styles.title}>MARKET DATA COULD NOT BE ANALYSED</h1>
      <p className={styles.code}>{code}</p>
      <p className={styles.message}>{message}</p>
    </section>
  )
}
