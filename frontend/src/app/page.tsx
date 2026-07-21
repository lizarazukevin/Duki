import Image from "next/image";
import { GoogleSignInButton } from "@/features/auth/google-sign-in-button";
import { PRODUCT_NAME } from "@/lib/constants";

export default function Home() {
  return (
    <main className="entry-page">
      <header className="masthead">
        <a className="wordmark" href="/" aria-label={`${PRODUCT_NAME} home`}>
          <span aria-hidden="true" className="wordmark-dot" />
          {PRODUCT_NAME}
        </a>
        <div className="masthead-note">
          <span>Personal planning</span>
          <span>Built for imperfect days</span>
        </div>
      </header>

      <section className="entry-grid" aria-labelledby="entry-heading">
        <div className="title-block">
          <p className="eyebrow">Mood-aware daily planning / 01</p>
          <h1 id="entry-heading">
            Plan the day.
            <br />
            <em>Debrief out loud.</em>
          </h1>
          <p className="lede">
            Duky turns the time you actually have—and the energy you actually
            feel—into a plan worth following.
          </p>
        </div>

        <figure className="duck-plate">
          <Image
            alt="A yellow rubber duck rendered in a tactile risograph style"
            className="duck-image"
            height={1408}
            priority
            src="/images/duky-editorial.png"
            width={1152}
          />
          <figcaption>
            <span>Fig. 01</span>
            <span>Your unflappable planning partner</span>
          </figcaption>
        </figure>

        <aside className="sign-in-panel" aria-labelledby="sign-in-heading">
          <p className="section-number">01 / Start here</p>
          <h2 id="sign-in-heading">Bring your calendar. Keep your agency.</h2>
          <p className="panel-copy">
            Connect Google to find open time and protect the commitments that
            already matter. Duky asks before changing your tasks.
          </p>
          <GoogleSignInButton />
          <p className="privacy-note">
            Calendar access is private to your account. You can disconnect at
            any time.
          </p>
        </aside>
      </section>

      <footer className="entry-footer">
        <p>Calendar-aware</p>
        <p>Voice-ready</p>
        <p>Human-confirmed</p>
        <span>© 2026 {PRODUCT_NAME}</span>
      </footer>
    </main>
  );
}
