export default function Login() {
  return <main style={{ maxWidth: 440, margin: "100px auto", padding: 24 }}>
    <h1>Sign in to AI Content Studio</h1>
    <p>Enter the Studio access token supplied by your administrator.</p>
    <form action="/api/session" method="post">
      <label htmlFor="token">Access token</label>
      <input id="token" name="token" type="password" required autoComplete="current-password" className="modern-input" />
      <button type="submit" className="modern-input">Sign in</button>
    </form>
  </main>;
}
