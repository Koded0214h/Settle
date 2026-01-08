# Settle

**Settle** is a "Gasless" Invoicing and Payment DApp designed specifically for the African gig economy. It functions as a Web3-native alternative to platforms like Payoneer or PayPal, but without the exorbitant fees, arbitrary account bans, or slow settlement times.

## 🚀 The Problem
African freelancers and remote workers face a "triple penalty" when earning globally:
1.  **Exorbitant Fees:** Traditional platforms charge 5-20% in fees.
2.  **Currency Devaluation:** Local currencies lose value rapidly; freelancers want to save in USD.
3.  **The "Crypto Barrier":** Existing wallets are too complex (seed phrases, gas fees) for non-technical users.

## 💡 The Solution
**Settle** bridges the gap between African talent and global capital using **Scroll's Layer 2** infrastructure.

* **Professional Invoicing:** Freelancers generate branded payment links (e.g., `settle.me/invoice/123`).
* **Gasless "Smart Accounts":** Leverages **ERC-4337 (Account Abstraction)** and **Paymasters** so users never need ETH for gas.
* **Instant Settlement:** Payments settle instantly in **USDC** on Scroll, with sub-cent transaction fees.

## 🛠 Tech Stack
* **Network:** [Scroll zkEVM](https://scroll.io/) (Layer 2)
* **Smart Contracts:** Solidity, OpenZeppelin
* **Backend:** Django
* **Account Abstraction:** ERC-4337 (Paymaster & Bundler integrations)
* **Frontend:** Next.js, Tailwind CSS, TypeScript
* **Tools:** BoltAI, Foundry

## 🗺 Roadmap
* **Phase 1 (Hackathon):** MVP development (Invoice generation, Gasless payments).
* **Phase 2:** Social Login integration (Google/Twitter).
* **Phase 3:** Fiat Off-ramp integration.

---
*Built for the KayabaLabs DApp Nursery 2025.*
