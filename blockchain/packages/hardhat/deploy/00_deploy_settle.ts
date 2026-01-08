import { HardhatRuntimeEnvironment } from "hardhat/types";
import { DeployFunction } from "hardhat-deploy/types";
import { Contract } from "ethers";

const deploySettleInvoicing: DeployFunction = async function (hre: HardhatRuntimeEnvironment) {
  const { deployer } = await hre.getNamedAccounts();
  const { deploy } = hre.deployments;

  // 1. Deploy MockUSDC first (useful for testing your frontend later)
  await deploy("MockUSDC", {
    from: deployer,
    args: [],
    log: true,
    autoMine: true,
  });

  // 2. Deploy SettleInvoicing
  await deploy("SettleInvoicing", {
    from: deployer,
    args: [],
    log: true,
    autoMine: true,
  });

  console.log("👋 Settle Contracts Deployed!");
};

export default deploySettleInvoicing;

// This tag helps you run specific scripts
deploySettleInvoicing.tags = ["SettleInvoicing"];