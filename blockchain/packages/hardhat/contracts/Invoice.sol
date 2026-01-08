// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title Settle: Gasless Invoicing for the African Gig Economy
 * @dev Optimized for Scroll L2 and ERC-4337 compatibility.
 */

// Interface for USDC (or any ERC20 token)
interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract SettleInvoicing {
    
    struct Invoice {
        address freelancer;
        address client;
        uint256 amount;
        uint256 dueDate;
        bool isPaid;
        string invoiceURI; // Link to IPFS for metadata (Description, logo, etc.)
    }

    // Storage
    mapping(uint256 => Invoice) public invoices;
    uint256 public invoiceCount;

    // Events for the Frontend to listen to
    event InvoiceCreated(uint256 indexed id, address indexed freelancer, uint256 amount);
    event InvoicePaid(uint256 indexed id, address indexed client);

    /**
     * @notice Freelancer registers a new invoice.
     * @param _amount Amount in USDC (usually 6 decimals)
     * @param _dueDate Unix timestamp for when payment is expected
     * @param _uri IPFS hash containing invoice metadata (No backend needed!)
     */
    function registerInvoice(
        uint256 _amount,
        uint256 _dueDate,
        string memory _uri
    ) public returns (uint256) {
        invoiceCount++;
        
        invoices[invoiceCount] = Invoice({
            freelancer: msg.sender,
            client: address(0), // Will be set when paid
            amount: _amount,
            dueDate: _dueDate,
            isPaid: false,
            invoiceURI: _uri
        });

        emit InvoiceCreated(invoiceCount, msg.sender, _amount);
        return invoiceCount;
    }

    /**
     * @notice Client pays the invoice using USDC.
     * @param _id The ID of the invoice to settle.
     * @param _usdcAddress The address of USDC on Scroll.
     */
    function payInvoice(uint256 _id, address _usdcAddress) public {
        Invoice storage inv = invoices[_id];
        
        require(!inv.isPaid, "Invoice already paid");
        require(inv.amount > 0, "Invoice does not exist");

        IERC20 usdc = IERC20(_usdcAddress);

        // Update state first (Safety against re-entrancy)
        inv.isPaid = true;
        inv.client = msg.sender;

        // Perform the transfer
        bool success = usdc.transferFrom(msg.sender, inv.freelancer, inv.amount);
        require(success, "USDC transfer failed. Check allowance.");

        emit InvoicePaid(_id, msg.sender);
    }

    // Helper to get invoice details for the frontend
    function getInvoice(uint256 _id) public view returns (Invoice memory) {
        return invoices[_id];
    }
}