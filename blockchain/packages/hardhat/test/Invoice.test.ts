import { expect } from "chai";
import { ethers } from "hardhat";
import { SettleInvoicing, MockUSDC } from "../typechain-types";
import { SignerWithAddress } from "@nomicfoundation/hardhat-ethers/signers";

describe("SettleInvoicing", function () {
  let settle: SettleInvoicing;
  let usdc: MockUSDC;
  let freelancer: SignerWithAddress;
  let client: SignerWithAddress;

  beforeEach(async () => {
    [freelancer, client] = await ethers.getSigners();

    // Deploy Mock USDC
    const MockUSDC = await ethers.getContractFactory("MockUSDC");
    usdc = await MockUSDC.deploy();

    // Deploy Settle
    const Settle = await ethers.getContractFactory("SettleInvoicing");
    settle = await Settle.deploy();

    // Give client some USDC and approve Settle contract
    await usdc.mint(client.address, ethers.parseUnits("1000", 6));
    await usdc.connect(client).approve(await settle.getAddress(), ethers.parseUnits("1000", 6));
  });

  it("Should register and pay an invoice", async function () {
    const amount = ethers.parseUnits("500", 6); // 500 USDC
    const dueDate = Math.floor(Date.now() / 1000) + 86400; // Tomorrow
    const ipfsHash = "ipfs://QmYourHashHere";

    // 1. Register
    await settle.connect(freelancer).registerInvoice(amount, dueDate, ipfsHash);
    
    // 2. Pay
    await expect(settle.connect(client).payInvoice(1, await usdc.getAddress()))
      .to.emit(settle, "InvoicePaid")
      .withArgs(1, client.address);

    // 3. Verify Balances
    expect(await usdc.balanceOf(freelancer.address)).to.equal(amount);
    const inv = await settle.getInvoice(1);
    expect(inv.isPaid).to.be.true;
  });
});