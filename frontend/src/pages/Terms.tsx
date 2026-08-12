import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

export default function Terms() {
  return (
    <div className="min-h-screen bg-zinc-50 pt-20 pb-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto bg-white p-8 sm:p-12 rounded-2xl shadow-sm border border-zinc-200">
        <Link to="/" className="inline-flex items-center text-sm font-medium text-brand hover:underline mb-8">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to home
        </Link>
        
        <h1 className="text-3xl font-bold text-zinc-900 mb-8">Terms of Service</h1>
        
        <div className="prose prose-zinc max-w-none text-zinc-600 space-y-6">
          <section>
            <h2 className="text-xl font-semibold text-zinc-900 mb-3">1. Acceptance of Terms</h2>
            <p>
              By accessing and using this Agentic Resume Builder, you agree to be bound by these Terms of Service. 
              If you do not agree to these terms, please do not use our service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-900 mb-3">2. AI-Generated Content Disclaimer</h2>
            <p>
              Our platform uses artificial intelligence (including models from OpenAI, Google, etc.) to analyze and generate resume content. 
              While we strive for high quality, AI can sometimes generate inaccurate, misleading, or hallucinated information.
            </p>
            <ul className="list-disc pl-5 mt-2 space-y-1 text-zinc-700 font-medium">
              <li>You are solely responsible for reviewing and verifying the accuracy of all generated resumes before using them to apply for jobs.</li>
              <li>We do not guarantee that using our service will result in job interviews or offers.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-900 mb-3">3. Data Privacy and Third-Party Services</h2>
            <p>
              To provide this service, the resumes and job descriptions you upload are transmitted to third-party AI providers via secure APIs. 
              We do not sell your personal data to advertisers. 
            </p>
            <p className="mt-2">
              However, please do not upload highly sensitive personal information (such as Social Security Numbers, banking details, or highly confidential company secrets) to the platform.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-900 mb-3">4. Acceptable Use</h2>
            <p>
              You agree not to misuse the platform. This includes, but is not limited to:
            </p>
            <ul className="list-disc pl-5 mt-2 space-y-1">
              <li>Using automated scripts, bots, or scrapers to generate resumes in bulk.</li>
              <li>Attempting to reverse engineer or bypass our rate limits and security measures.</li>
              <li>Uploading malicious files or attempting to inject harmful code into our parsers.</li>
            </ul>
            <p className="mt-2">
              We reserve the right to suspend or terminate accounts that violate these terms without prior notice.
            </p>
          </section>
          
          <section>
            <h2 className="text-xl font-semibold text-zinc-900 mb-3">5. Changes to Terms</h2>
            <p>
              We may update these terms occasionally. Your continued use of the service after changes are made constitutes your acceptance of the new terms.
            </p>
          </section>
        </div>
        
        <div className="mt-12 pt-8 border-t border-zinc-100 text-sm text-zinc-500">
          Last updated: {new Date().toLocaleDateString()}
        </div>
      </div>
    </div>
  )
}
