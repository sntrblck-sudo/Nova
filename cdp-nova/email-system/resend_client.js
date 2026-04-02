/**
 * Nova's Email System - Resend API Client
 * Sends email via Resend API (resend.com)
 * 
 * Setup: Get API key from https://resend.com/api-keys
 * Add to environment: RESEND_API_KEY=re_xxxxx
 */

const { Resend } = require('resend');

class ResendClient {
  constructor(apiKey) {
    if (!apiKey) {
      throw new Error('RESEND_API_KEY not configured');
    }
    this.client = new Resend(apiKey);
    this.fromEmail = process.env.EMAIL_FROM || 'nova@resend.dev';
  }

  async send({ to, subject, text, html, replyTo }) {
    const params = {
      from: this.fromEmail,
      to: Array.isArray(to) ? to : [to],
      subject,
      text,
      html: html || text,
      ...(replyTo && { reply_to: replyTo }),
    };

    const result = await this.client.emails.send(params);
    return result;
  }

  async sendWithTracking({ to, subject, text, html, tags }) {
    const params = {
      from: this.fromEmail,
      to: Array.isArray(to) ? to : [to],
      subject,
      text,
      html: html || text,
      tags: tags || [],
    };

    return this.client.emails.send(params);
  }
}

module.exports = { ResendClient };
