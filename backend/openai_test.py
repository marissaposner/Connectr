import os
import openai
# from llama_index import (
#     LLMPredictor,
#     GPTSimpleVectorIndex,
#     SimpleDirectoryReader,
#     PromptHelper,
# )
# from llama_index.indices import GPTListIndex
# from llama_index import Document

import requests
import json
schema = """# Subgraph Schema: Lending Protocol
# Version: 3.1.0
# See https://github.com/messari/subgraphs/blob/master/docs/SCHEMA.md for details

enum Network {
  ARBITRUM_ONE
  ARWEAVE_MAINNET
  AURORA
  AVALANCHE
  BOBA
  BSC # aka BNB Chain
  CELO
  COSMOS
  CRONOS
  MAINNET # Ethereum Mainnet
  FANTOM
  FUSE
  HARMONY
  JUNO
  MOONBEAM
  MOONRIVER
  NEAR_MAINNET
  OPTIMISM
  OSMOSIS
  MATIC # aka Polygon
  GNOSIS
}

enum ProtocolType {
  EXCHANGE
  LENDING
  YIELD
  BRIDGE
  GENERIC
  # Will add more
}

type Token @entity @regularPolling {
  " Smart contract address of the token "
  id: Bytes!

  " Name of the token, mirrored from the smart contract "
  name: String!

  " Symbol of the token, mirrored from the smart contract "
  symbol: String!

  " The number of decimal places this token uses, default to 18 "
  decimals: Int!

  " Optional field to track the price of a token, mostly for caching purposes "
  lastPriceUSD: BigDecimal

  " Optional field to track the block number of the last token price "
  lastPriceBlockNumber: BigInt

  " The type of token the protocol creates for positions "
  type: TokenType
}

enum RewardTokenType {
  " For reward tokens awarded to LPs/lenders "
  DEPOSIT

  " For reward tokens awarded to borrowers of variable debt "
  VARIABLE_BORROW

  " For reward tokens awarded to borrowers of stable debt "
  STABLE_BORROW

  " For reward tokens awarded to stakers "
  STAKE
}

type RewardToken @entity(immutable: true) @regularPolling {
  " { Reward token type }-{ Smart contract address of the reward token } "
  id: ID!

  " Reference to the actual token "
  token: Token!

  " The type of the reward token "
  type: RewardTokenType!
}

enum LendingType {
  " Collateralized Debt Position (CDP) protocols have singular isolated positions created by users. We aggregate them to give a single view of a market "
  CDP

  " Pooled protocols pool all users assets into a single market "
  POOLED
}

enum PermissionType {
  " Only users that have been whitelisted can interact. e.g. Only approved institutions can borrow "
  WHITELIST_ONLY

  " To interact a user must be KYC'd "
  PERMISSIONED

  " Protocols that do not KYC. Can be used by any account "
  PERMISSIONLESS

  " Only the protocol admin address can make do the defined actions "
  ADMIN
}

enum RiskType {
  " Global risk means each users position in a market is combined for one score to determine if they can be liquidated "
  GLOBAL

  " Isolated risk means each users position in a market or CDP is isolated for risk of liquidation "
  ISOLATED
}

enum CollateralizationType {
  " Over collateralized protocols require users to put up more collateral than the amount borrowed. "
  OVER_COLLATERALIZED

  " Protocols that allow users to borrow more than their collateral locked.  "
  UNDER_COLLATERALIZED

  " Protocols that allow users to borrow without any collateral. Generally this protocol is KYC'd and only whitelist users can do this "
  UNCOLLATERALIZED
}

# This is used for representative token descriptions
# e.g. collateral or debt tokens in a protocol
enum TokenType {
  " Rebasing tokens continuously adjust balances / supply as interest is accrued (e.g. Aave debt balances adjust at each block with interest) "
  REBASING

  " Non-rebasing token balances / supply do not change as interest is accrued (e.g. Compound's cToken's do not adjust balance, the exchange rate changes with interest) "
  NON_REBASING
}

enum InterestRateType {
  " Stable interest rate (e.g. Aave) "
  STABLE

  " Variable interest rate (e.g. Compound) "
  VARIABLE

  " Fixed interest rate (e.g. Notional) "
  FIXED
}

enum InterestRateSide {
  " Interest rate accrued by lenders "
  LENDER

  " Interest rate paid by borrowers "
  BORROWER
}

enum Tranche {
  " Senior denotes debt with a higher priority. The first debt to be paid back to lenders. "
  SENIOR

  " Junior tranche denotes lower priority debt. This is secondary priority to be paid back to lenders. "
  JUNIOR
}

enum PositionSide {
  " Position opened as a lender (used as collateral) "
  COLLATERAL

  " Position opened as a borrower "
  BORROWER
}

# Most markets only have a single interest rate given a specific type.
# However, fixed term lending protocols can have multiple rates with
# different duration/maturity per market. You can append a counter
# to the IDs to differentiate.
type InterestRate @entity @regularPolling {
  " { Interest rate side }-{ Interest rate type }-{ Market ID }-{ Optional: Tranche }-{ Optional: # days/hours since epoch time } "
  id: ID!

  " Interest rate in percentage APY. E.g. 5.21% should be stored as 5.21 "
  rate: BigDecimal!

  " Duration of the loan in days. Only applies to fixed term lending (e.g. Notional) "
  duration: Int

  " Maturity of the loan in block height. Only applies to fixed term lending (e.g. Notional) "
  maturityBlock: BigInt

  " The party the interest is paid to / received from "
  side: InterestRateSide!

  " The type of interest rate (e.g. stable, fixed, variable, etc) "
  type: InterestRateType!

  " The level of debt priority at this interest rate "
  tranche: Tranche
}

enum FeeType {
  " Fees from liquidations "
  LIQUIDATION_FEE

  " Fees given to an admin "
  ADMIN_FEE

  " Fees that are taken by the protocol "
  PROTOCOL_FEE

  " Fee to mint an asset. Found mostly in CDPs "
  MINT_FEE

  " Fee taken on withdrawal. e.g. found in Euler "
  WITHDRAW_FEE

  " Flashloan Fees taken by the protocol "
  FLASHLOAN_PROTOCOL_FEE

  " Flashloan Fees taken by LP "
  FLASHLOAN_LP_FEE

  " Any fee not represented here. Please make a github issue for this to be added: https://github.com/messari/subgraphs/issues/new "
  OTHER
}

type Fee @entity @regularPolling {
  " { Fee type } "
  id: ID!

  " Fee in percentage. E.g. 5.21% should be stored as 5.21 "
  rate: BigDecimal

  " A flat fee in the native token. This may be a base fee in addition to the rate, or the only fee. "
  flatFee: BigDecimal

  " The type of fee (e.g. liquidation, admin, etc.) "
  type: FeeType!
}

# This entity offers a more nuanced view of revenue types
# Use this to provide the sources of revenue and amounts of each
type RevenueDetail @entity @regularPolling {
  " { Market/Protocol ID }{ Optional: Snapshot ID } "
  id: Bytes!

  " The source of revenue (in alphabetical order) "
  sources: [Fee!]!

  " The amount of revenue in USD (same order as sources) "
  amountsUSD: [BigDecimal!]!
}

enum OracleSource {
  UNISWAP
  BALANCER
  CHAINLINK
  YEARN
  SUSHISWAP
  CURVE
  ## Can add more
}

# Most lending protocols get token prices through onchain oracles.
# As oracles are a source of truth it is important to understand the details.
# This entity will help track oracle-related data in a market
type Oracle @entity @regularPolling {
  " { Market Address }{ Token Address } "
  id: Bytes!

  oracleAddress: Bytes!

  " The market that this oracle is used for pricing "
  market: Market!

  " The block this oracle was adopted for a market "
  blockCreated: BigInt!

  " The timestamp this oracle was adopted for a market "
  timestampCreated: BigInt!

  " Is the Oracle currently used as the source of truth for a market"
  isActive: Boolean!

  " True if the oracle returns prices in USD (e.g. generally the other case is the network's native token) "
  isUSD: Boolean!

  " The hash where the oracle was no longer used "
  hashEnded: Bytes

  " The Protocol that is providing the oracle (nullable if non-standard source)"
  oracleSource: OracleSource
}

#############################
##### Protocol Metadata #####
#############################

interface Protocol {
  " Smart contract address of the protocol's main contract (Factory, Registry, etc) "
  id: Bytes!

  " Base name of the protocol, excluding transformations. e.g. Aave "
  protocol: String!

  " Name of the protocol, including version. e.g. Aave v2 "
  name: String!

  " Slug of protocol, including version. e.g. aave-v2 "
  slug: String!

  " Version of the subgraph schema, in SemVer format (e.g. 1.0.0) "
  schemaVersion: String!

  " Version of the subgraph implementation, in SemVer format (e.g. 1.0.0) "
  subgraphVersion: String!

  " Version of the methodology used to compute metrics, loosely based on SemVer format (e.g. 1.0.0) "
  methodologyVersion: String!

  " The blockchain network this subgraph is indexing on "
  network: Network!

  " The type of protocol (e.g. DEX, Lending, Yield, etc) "
  type: ProtocolType!

  " The specific lending protocol type "
  lendingType: LendingType

  " The specific permissions required to lend in this protocol "
  lenderPermissionType: PermissionType

  " The specific permissions required to borrow from this protocol "
  borrowerPermissionType: PermissionType

  " The specific permissions required to create a pool (market) in this protocol "
  poolCreatorPermissionType: PermissionType

  " Risk type of the lending protocol "
  riskType: RiskType

  " The way a positions can be collateralized "
  collateralizationType: CollateralizationType

  ##### Quantitative Data #####

  " Current TVL (Total Value Locked) of the entire protocol "
  totalValueLockedUSD: BigDecimal!

  " Current PCV (Protocol Controlled Value). Only relevant for protocols with PCV. "
  protocolControlledValueUSD: BigDecimal

  " Number of cumulative unique users. e.g. accounts that spent gas to interact with this protocol "
  cumulativeUniqueUsers: Int!

  " Revenue claimed by suppliers to the protocol. LPs on DEXs (e.g. 0.25% of the swap fee in Sushiswap). Depositors on Lending Protocols. NFT sellers on OpenSea. "
  cumulativeSupplySideRevenueUSD: BigDecimal!

  " Gross revenue for the protocol (revenue claimed by protocol). Examples: AMM protocol fee (Sushi’s 0.05%). OpenSea 10% sell fee. "
  cumulativeProtocolSideRevenueUSD: BigDecimal!

  " All revenue generated by the protocol. e.g. 0.30% of swap fee in Sushiswap, all yield generated by Yearn. "
  cumulativeTotalRevenueUSD: BigDecimal!

  " Total number of pools "
  totalPoolCount: Int!

  ##### Snapshots #####

  " Daily usage metrics for this protocol "
  dailyUsageMetrics: [UsageMetricsDailySnapshot!]!
    @derivedFrom(field: "protocol")

  " Hourly usage metrics for this protocol "
  hourlyUsageMetrics: [UsageMetricsHourlySnapshot!]!
    @derivedFrom(field: "protocol")

  " Daily financial metrics for this protocol "
  financialMetrics: [FinancialsDailySnapshot!]! @derivedFrom(field: "protocol")
}

type LendingProtocol implements Protocol @entity @regularPolling {
  " Smart contract address of the protocol's main contract (Factory, Registry, etc) "
  id: Bytes!

  " Base name of the protocol, excluding transformations. e.g. Aave "
  protocol: String!

  " Name of the protocol, including version. e.g. Aave v2 "
  name: String!

  " Slug of protocol, including version. e.g. aave-v2 "
  slug: String!

  " Version of the subgraph schema, in SemVer format (e.g. 1.0.0) "
  schemaVersion: String!

  " Version of the subgraph implementation, in SemVer format (e.g. 1.0.0) "
  subgraphVersion: String!

  " Version of the methodology used to compute metrics, loosely based on SemVer format (e.g. 1.0.0) "
  methodologyVersion: String!

  " The blockchain network this subgraph is indexing on "
  network: Network!

  " The type of protocol (e.g. DEX, Lending, Yield, etc) "
  type: ProtocolType!

  " The specific lending protocol type "
  lendingType: LendingType

  " The specific permissions required to lend in this protocol "
  lenderPermissionType: PermissionType

  " The specific permissions required to borrow from this protocol "
  borrowerPermissionType: PermissionType

  " The specific permissions required to create a pool (market) in this protocol "
  poolCreatorPermissionType: PermissionType

  " Risk type of the lending protocol "
  riskType: RiskType

  " The way a positions can be collateralized "
  collateralizationType: CollateralizationType

  " Tokens that can be minted. Only applies to CDP (usually stable coins) "
  mintedTokens: [Token!]

  " Additional tokens that are given as reward for position in a protocol, usually in liquidity mining programs. "
  rewardTokens: [RewardToken!]

  ##### Quantitative Data #####

  " Number of cumulative unique users. e.g. accounts that spent gas to interact with this protocol "
  cumulativeUniqueUsers: Int!

  " Number of cumulative depositors "
  cumulativeUniqueDepositors: Int!

  " Number of cumulative borrowers "
  cumulativeUniqueBorrowers: Int!

  " Number of cumulative liquidators (accounts that performed liquidation) "
  cumulativeUniqueLiquidators: Int!

  " Number of cumulative liquidatees (accounts that got liquidated) "
  cumulativeUniqueLiquidatees: Int!

  " Current TVL (Total Value Locked) of the entire protocol "
  totalValueLockedUSD: BigDecimal!

  " Current PCV (Protocol Controlled Value). Only relevant for protocols with PCV. "
  protocolControlledValueUSD: BigDecimal

  " Revenue claimed by suppliers to the protocol. LPs on DEXs (e.g. 0.25% of the swap fee in Sushiswap). Depositors on Lending Protocols. NFT sellers on OpenSea. "
  cumulativeSupplySideRevenueUSD: BigDecimal!

  " Gross revenue for the protocol (revenue claimed by protocol). Examples: AMM protocol fee (Sushi’s 0.05%). OpenSea 10% sell fee. "
  cumulativeProtocolSideRevenueUSD: BigDecimal!

  " All revenue generated by the protocol. e.g. 0.30% of swap fee in Sushiswap, all yield generated by Yearn. "
  cumulativeTotalRevenueUSD: BigDecimal!

  " All fees in the protocol. Fee should be in percentage format. e.g. 0.30% liquidation fee "
  fees: [Fee!]

  " Details of revenue sources and amounts "
  revenueDetail: RevenueDetail

  " Current balance of all deposited assets, in USD. Note this metric should be the same as TVL. "
  totalDepositBalanceUSD: BigDecimal!

  " Sum of all historical deposits in USD (only considers deposits and not withdrawals) "
  cumulativeDepositUSD: BigDecimal!

  " Current balance of all borrowed/minted assets (not historical cumulative), in USD. "
  totalBorrowBalanceUSD: BigDecimal!

  " Sum of all historical borrows/mints in USD (i.e. total loan origination). "
  cumulativeBorrowUSD: BigDecimal!

  " Sum of all historical liquidations in USD "
  cumulativeLiquidateUSD: BigDecimal!

  " Total supply of minted tokens in native amounts, with same ordering as mintedTokens. Only applies to CDP "
  mintedTokenSupplies: [BigInt!]

  " Total number of pools "
  totalPoolCount: Int!

  " Total number of open positions "
  openPositionCount: Int!

  " Total number of positions (open and closed) "
  cumulativePositionCount: Int!

  " Total number of transactions "
  transactionCount: Int!

  " Total number of deposits "
  depositCount: Int!

  " Total number of withdrawals "
  withdrawCount: Int!

  " Total number of borrows "
  borrowCount: Int!

  " Total number of repayments "
  repayCount: Int!

  " Total number of liquidations "
  liquidationCount: Int!

  " Total number of transfers "
  transferCount: Int!

  " Total number of flashloans "
  flashloanCount: Int!

  ##### Token Balances #####

  " Per-block reward token emission as of the current block normalized to a day, in token's native amount. This should be ideally calculated as the theoretical rate instead of the realized amount. "
  rewardTokenEmissionsAmount: [BigInt!]

  " Per-block reward token emission as of the current block normalized to a day, in USD value. This should be ideally calculated as the theoretical rate instead of the realized amount. "
  rewardTokenEmissionsUSD: [BigDecimal!]

  ##### Snapshots #####

  " Daily usage metrics for this protocol "
  dailyUsageMetrics: [UsageMetricsDailySnapshot!]!
    @derivedFrom(field: "protocol")

  " Hourly usage metrics for this protocol "
  hourlyUsageMetrics: [UsageMetricsHourlySnapshot!]!
    @derivedFrom(field: "protocol")

  " Daily financial metrics for this protocol "
  financialMetrics: [FinancialsDailySnapshot!]! @derivedFrom(field: "protocol")

  ##### Markets #####

  " All markets that belong to this protocol "
  markets: [Market!]! @derivedFrom(field: "protocol")
}

# helper entity to iterate through all markets
type _MarketList @entity {
  " Same ID as LendingProtocol "
  id: Bytes!

  " IDs of all markets in the LendingProtocol "
  markets: [Bytes!]!
}

###############################
##### Protocol Timeseries #####
###############################

type UsageMetricsDailySnapshot @entity @dailySnapshot {
  " ID is # of days since Unix epoch time "
  id: Bytes!

  " Number of days since Unix epoch time "
  days: Int!

  " Protocol this snapshot is associated with "
  protocol: LendingProtocol!

  " Number of unique daily active users. e.g. accounts that spent gas to interact with this protocol "
  dailyActiveUsers: Int!

  " Number of cumulative unique users. e.g. accounts that spent gas to interact with this protocol "
  cumulativeUniqueUsers: Int!

  " Number of unique daily depositors "
  dailyActiveDepositors: Int!

  " Number of cumulative depositors "
  cumulativeUniqueDepositors: Int!

  " Number of unique daily borrowers "
  dailyActiveBorrowers: Int!

  " Number of cumulative borrowers "
  cumulativeUniqueBorrowers: Int!

  " Number of unique daily liquidators (accounts that performed liquidation) "
  dailyActiveLiquidators: Int!

  " Number of cumulative liquidators (accounts that performed liquidation) "
  cumulativeUniqueLiquidators: Int!

  " Number of unique daily liquidatees (accounts that got liquidated) "
  dailyActiveLiquidatees: Int!

  " Number of cumulative liquidatees (accounts that got liquidated) "
  cumulativeUniqueLiquidatees: Int!

  " Total number of transactions occurred in a day. Transactions include all entities that implement the Event interface. "
  dailyTransactionCount: Int!

  " Total number of deposits in a day "
  dailyDepositCount: Int!

  " Total number of withdrawals in a day "
  dailyWithdrawCount: Int!

  " Total number of borrows/mints in a day "
  dailyBorrowCount: Int!

  " Total number of repayments/burns in a day "
  dailyRepayCount: Int!

  " Total number of liquidations in a day "
  dailyLiquidateCount: Int!

  " Total number of transfers in a day "
  dailyTransferCount: Int!

  " Total number of flashloans in a day "
  dailyFlashloanCount: Int!

  " Total number of positions (open and closed) "
  cumulativePositionCount: Int!

  " Total number of open positions "
  openPositionCount: Int!

  " Total number of positions touched in a day. This includes opening, closing, and modifying positions. "
  dailyActivePositions: Int!

  " Total number of pools "
  totalPoolCount: Int!

  " Block number of this snapshot "
  blockNumber: BigInt!

  " Timestamp of this snapshot "
  timestamp: BigInt!
}

type UsageMetricsHourlySnapshot @entity @hourlySnapshot {
  " { # of hours since Unix epoch time } "
  id: Bytes!

  " Number of hours since Unix epoch time "
  hours: Int!

  " Protocol this snapshot is associated with "
  protocol: LendingProtocol!

  " Number of unique hourly active users "
  hourlyActiveUsers: Int!

  " Number of cumulative unique users. e.g. accounts that spent gas to interact with this protocol "
  cumulativeUniqueUsers: Int!

  " Total number of transactions occurred in an hour. Transactions include all entities that implement the Event interface. "
  hourlyTransactionCount: Int!

  " Total number of deposits in an hour "
  hourlyDepositCount: Int!

  " Total number of withdrawals in an hour "
  hourlyWithdrawCount: Int!

  " Total number of borrows/mints in an hour "
  hourlyBorrowCount: Int!

  " Total number of repayments/burns in an hour "
  hourlyRepayCount: Int!

  " Total number of liquidations in an hour "
  hourlyLiquidateCount: Int!

  " Block number of this snapshot "
  blockNumber: BigInt!

  " Timestamp of this snapshot "
  timestamp: BigInt!
}

type FinancialsDailySnapshot @entity @dailySnapshot {
  " ID is # of days since Unix epoch time "
  id: Bytes!

  " Number of days since Unix epoch time "
  days: Int!

  " Protocol this snapshot is associated with "
  protocol: LendingProtocol!

  " Block number of this snapshot "
  blockNumber: BigInt!

  " Timestamp of this snapshot "
  timestamp: BigInt!

  " Current TVL (Total Value Locked) of the entire protocol "
  totalValueLockedUSD: BigDecimal!

  " Current PCV (Protocol Controlled Value). Only relevant for protocols with PCV. "
  protocolControlledValueUSD: BigDecimal

  " Total supply of minted tokens in native amounts, with same ordering as mintedTokens. Only applies to CDP "
  mintedTokenSupplies: [BigInt!]

  ##### Revenue #####

  " Revenue claimed by suppliers to the protocol. LPs on DEXs (e.g. 0.25% of the swap fee in Sushiswap). Depositors on Lending Protocols. NFT sellers on OpenSea. "
  dailySupplySideRevenueUSD: BigDecimal!

  " Revenue claimed by suppliers to the protocol. LPs on DEXs (e.g. 0.25% of the swap fee in Sushiswap). Depositors on Lending Protocols. NFT sellers on OpenSea. "
  cumulativeSupplySideRevenueUSD: BigDecimal!

  " Gross revenue for the protocol (revenue claimed by protocol). Examples: AMM protocol fee (Sushi’s 0.05%). OpenSea 10% sell fee. "
  dailyProtocolSideRevenueUSD: BigDecimal!

  " Gross revenue for the protocol (revenue claimed by protocol). Examples: AMM protocol fee (Sushi’s 0.05%). OpenSea 10% sell fee. "
  cumulativeProtocolSideRevenueUSD: BigDecimal!

  " All revenue generated by the protocol. e.g. 0.30% of swap fee in Sushiswap, all yield generated by Yearn. "
  dailyTotalRevenueUSD: BigDecimal!

  " All revenue generated by the protocol. e.g. 0.30% of swap fee in Sushiswap, all yield generated by Yearn. "
  cumulativeTotalRevenueUSD: BigDecimal!

  " Details of revenue sources and amounts "
  revenueDetail: RevenueDetail

  ##### Lending Activities #####

  " Current balance of all deposited assets, in USD. Note this metric should be the same as TVL. "
  totalDepositBalanceUSD: BigDecimal!

  " Total assets deposited on a given day, in USD "
  dailyDepositUSD: BigDecimal!

  " Sum of all historical deposits in USD (only considers deposits and not withdrawals) "
  cumulativeDepositUSD: BigDecimal!

  " Current balance of all borrowed/minted assets, in USD. "
  totalBorrowBalanceUSD: BigDecimal!

  " Total assets borrowed/minted on a given day, in USD. "
  dailyBorrowUSD: BigDecimal!

  " Sum of all historical borrows/mints in USD (i.e. total loan origination). "
  cumulativeBorrowUSD: BigDecimal!

  " Total assets liquidated on a given day, in USD. "
  dailyLiquidateUSD: BigDecimal!

  " Sum of all historical liquidations in USD "
  cumulativeLiquidateUSD: BigDecimal!

  " Total assets withdrawn on a given day, in USD. "
  dailyWithdrawUSD: BigDecimal!

  " Total assets repaid on a given day, in USD. "
  dailyRepayUSD: BigDecimal!

  " Total assets transferred on a given day, in USD. "
  dailyTransferUSD: BigDecimal!

  " Total flashloans executed on a given day, in USD. "
  dailyFlashloanUSD: BigDecimal!
}

###############################
##### Pool-Level Metadata #####
###############################

"""
"""
type Market @entity @regularPolling {
  " Smart contract address of the market "
  id: Bytes!

  " The protocol this pool belongs to "
  protocol: LendingProtocol!

  " Name of market "
  name: String

  " Is this market active or is it frozen "
  isActive: Boolean!

  " Can you borrow from this market "
  canBorrowFrom: Boolean!

  " Can you use the output token as collateral "
  canUseAsCollateral: Boolean!

  " Maximum loan-to-value ratio as a percentage value (e.g. 75% for DAI in Aave) "
  maximumLTV: BigDecimal!

  " Liquidation threshold as a percentage value (e.g. 80% for DAI in Aave). When it is reached, the position is defined as undercollateralised and could be liquidated "
  liquidationThreshold: BigDecimal!

  " Liquidation penalty (or the liquidation bonus for liquidators) as a percentage value. It is the penalty/bonus price on the collateral when liquidators purchase it as part of the liquidation of a loan that has passed the liquidation threshold "
  liquidationPenalty: BigDecimal!

  " Can the user choose to isolate assets in this market. e.g. only this market's collateral can be used for a borrow in Aave V3 "
  canIsolate: Boolean!

  " Creation timestamp "
  createdTimestamp: BigInt!

  " Creation block number "
  createdBlockNumber: BigInt!

  " Details about the price oracle used to get this token's price "
  oracle: Oracle

  " A unique identifier that can relate multiple markets. e.g. a common address that is the same for each related market. This is useful for markets with multiple input tokens "
  relation: Bytes

  ##### Incentives #####

  " Additional tokens that are given as reward for position in a protocol, usually in liquidity mining programs. e.g. SUSHI in the Onsen program, MATIC for Aave Polygon "
  rewardTokens: [RewardToken!]

  " Per-block reward token emission as of the current block normalized to a day, in token's native amount. This should be ideally calculated as the theoretical rate instead of the realized amount. "
  rewardTokenEmissionsAmount: [BigInt!]

  " Per-block reward token emission as of the current block normalized to a day, in USD value. This should be ideally calculated as the theoretical rate instead of the realized amount. "
  rewardTokenEmissionsUSD: [BigDecimal!]

  " Total supply of output tokens that are staked. Used to calculate reward APY. "
  stakedOutputTokenAmount: BigInt

  ##### Quantitative Data #####

  " Token that need to be deposited in this market to take a position in protocol (should be alphabetized) "
  inputToken: Token!

  " Amount of input token in the market (same order as inputTokens) "
  inputTokenBalance: BigInt!

  " Prices in USD of the input token (same order as inputTokens) "
  inputTokenPriceUSD: BigDecimal!

  " Tokens that are minted to track ownership of position in protocol (e.g. aToken, cToken). Leave as null if doesn't exist (should be alphabetized) "
  outputToken: Token

  " Total supply of output token (same order as outputTokens) "
  outputTokenSupply: BigInt

  " Prices in USD of the output token (same order as outputTokens) "
  outputTokenPriceUSD: BigDecimal

  " Amount of input token per full share of output token. Only applies when the output token exists (note this is a ratio and not a percentage value, i.e. 1.05 instead of 105%) "
  exchangeRate: BigDecimal

  " All interest rates for this input token. Should be in APR format "
  rates: [InterestRate!]

  " Total amount of reserves (in USD) "
  reserves: BigDecimal

  " The amount of revenue that is converted to reserves at the current time. 20% reserve factor should be in format 0.20 "
  reserveFactor: BigDecimal

  " The token that can be borrowed (e.g. inputToken in POOLED and generally a stable in CDPs) "
  borrowedToken: Token

  " Amount of input tokens borrowed in this market using variable interest rates (in native terms) "
  variableBorrowedTokenBalance: BigInt

  " Amount of input tokens borrowed in this market using stable interest rates (in native terms) "
  stableBorrowedTokenBalance: BigInt

  " Last updated timestamp of supply/borrow index. "
  indexLastUpdatedTimestamp: BigInt

  " Index used by the protocol to calculate interest generated on the supply token (ie, liquidityIndex in Aave)"
  supplyIndex: BigInt

  " Allowed limit to how much of the underlying asset can be supplied to this market. "
  supplyCap: BigInt

  " Index used by the protocol to calculate the interest paid on the borrowed token (ie, variableBorrowIndex in Aave))"
  borrowIndex: BigInt

  " Allowed limit for how much of the underlying asset can be borrowed from this market. "
  borrowCap: BigInt

  " Current TVL (Total Value Locked) of this market "
  totalValueLockedUSD: BigDecimal!

  " All revenue generated by the market, accrued to the supply side. "
  cumulativeSupplySideRevenueUSD: BigDecimal!

  " All revenue generated by the market, accrued to the protocol. "
  cumulativeProtocolSideRevenueUSD: BigDecimal!

  " All revenue generated by the market. "
  cumulativeTotalRevenueUSD: BigDecimal!

  " Details of revenue sources and amounts "
  revenueDetail: RevenueDetail

  " Current balance of all deposited assets (not historical cumulative), in USD "
  totalDepositBalanceUSD: BigDecimal!

  " Sum of all historical deposits in USD (only considers deposits and not withdrawals) "
  cumulativeDepositUSD: BigDecimal!

  " Current balance of all borrowed/minted assets (not historical cumulative), in USD "
  totalBorrowBalanceUSD: BigDecimal!

  " Sum of all historical borrows/mints in USD (i.e. total loan origination) "
  cumulativeBorrowUSD: BigDecimal!

  " Sum of all historical liquidations in USD "
  cumulativeLiquidateUSD: BigDecimal!

  " Sum of all historical transfers in USD "
  cumulativeTransferUSD: BigDecimal!

  " Sum of all historical flashloans in USD "
  cumulativeFlashloanUSD: BigDecimal!

  " Total number of transactions "
  transactionCount: Int!

  " Total number of deposits "
  depositCount: Int!

  " Total number of withdrawals "
  withdrawCount: Int!

  " Total number of borrows "
  borrowCount: Int!

  " Total number of repayments "
  repayCount: Int!

  " Total number of liquidations "
  liquidationCount: Int!

  " Total number of transfers "
  transferCount: Int!

  " Total number of flashloans "
  flashloanCount: Int!

  ##### Usage Data #####

  " Number of cumulative unique users. e.g. accounts that spent gas to interact with this market "
  cumulativeUniqueUsers: Int!

  " Number of cumulative depositors "
  cumulativeUniqueDepositors: Int!

  " Number of cumulative borrowers "
  cumulativeUniqueBorrowers: Int!

  " Number of cumulative liquidators (accounts that performed liquidation) "
  cumulativeUniqueLiquidators: Int!

  " Number of cumulative liquidatees (accounts that got liquidated) "
  cumulativeUniqueLiquidatees: Int!

  " Number of cumulative accounts that transferred positions (generally in the form of outputToken transfer) "
  cumulativeUniqueTransferrers: Int!

  " Number of cumulative accounts that performed flashloans "
  cumulativeUniqueFlashloaners: Int!

  ##### Account/Position Data #####

  " All positions in this market "
  positions: [Position!]! @derivedFrom(field: "market")

  " Number of positions in this market "
  positionCount: Int!

  " Number of open positions in this market "
  openPositionCount: Int!

  " Number of closed positions in this market "
  closedPositionCount: Int!

  " Number of lending positions in this market. Note: this is cumulative and strictly increasing "
  lendingPositionCount: Int!

  " Number of borrowing positions in this market. Note: this is cumulative and strictly increasing "
  borrowingPositionCount: Int!

  ##### Snapshots #####

  " Market daily snapshots "
  dailySnapshots: [MarketDailySnapshot!]! @derivedFrom(field: "market")

  " Market hourly snapshots "
  hourlySnapshots: [MarketHourlySnapshot!]! @derivedFrom(field: "market")

  ##### Events #####

  " All deposits made to this market "
  deposits: [Deposit!]! @derivedFrom(field: "market")

  " All withdrawals made from this market "
  withdraws: [Withdraw!]! @derivedFrom(field: "market")

  " All borrows from this market "
  borrows: [Borrow!]! @derivedFrom(field: "market")

  " All repayments to this market "
  repays: [Repay!]! @derivedFrom(field: "market")

  " All liquidations made to this market "
  liquidates: [Liquidate!]! @derivedFrom(field: "market")

  " All transfers made in this market "
  transfers: [Transfer!]! @derivedFrom(field: "market")

  " All flashloans made in this market"
  flashloans: [Flashloan!]! @derivedFrom(field: "market")
}

#################################
##### Pool-Level Timeseries #####
#################################

type MarketDailySnapshot @entity @dailySnapshot {
  " { Smart contract address of the market }{ # of days since Unix epoch time } "
  id: Bytes!

  " Number of days since Unix epoch time "
  days: Int!

  " The protocol this snapshot belongs to "
  protocol: LendingProtocol!

  " The pool this snapshot belongs to "
  market: Market!

  " Block number of this snapshot "
  blockNumber: BigInt!

  " Timestamp of this snapshot "
  timestamp: BigInt!

  " A unique identifier that can relate multiple markets together. e.g. a common address that they all share. This is useful for markets with multiple input tokens "
  relation: Bytes

  ##### Incentives #####

  " Additional tokens that are given as reward for position in a protocol, usually in liquidity mining programs. e.g. SUSHI in the Onsen program, MATIC for Aave Polygon "
  rewardTokens: [RewardToken!]

  " Per-block reward token emission as of the current block normalized to a day, in token's native amount. This should be ideally calculated as the theoretical rate instead of the realized amount. "
  rewardTokenEmissionsAmount: [BigInt!]

  " Per-block reward token emission as of the current block normalized to a day, in USD value. This should be ideally calculated as the theoretical rate instead of the realized amount. "
  rewardTokenEmissionsUSD: [BigDecimal!]

  " Total supply of output tokens that are staked. Used to calculate reward APY. "
  stakedOutputTokenAmount: BigInt

  ##### Quantitative Data #####

  " Amount of input token in the market (same order as inputTokens) "
  inputTokenBalance: BigInt!

  " Prices in USD of the input token (same order as inputTokens) "
  inputTokenPriceUSD: BigDecimal!

  " Total supply of output token (same order as outputTokens) "
  outputTokenSupply: BigInt

  " Prices in USD of the output token (same order as outputTokens) "
  outputTokenPriceUSD: BigDecimal

  " Amount of input token per full share of output token. Only applies when the output token exists (note this is a ratio and not a percentage value, i.e. 1.05 instead of 105%) "
  exchangeRate: BigDecimal

  " All interest rates for this input token. Should be in APR format "
  rates: [InterestRate!]

  " Total amount of reserves (in USD) "
  reserves: BigDecimal

  " The amount of revenue that is converted to reserves at the current time. 20% reserve factor should be in format 0.20 "
  reserveFactor: BigDecimal

  " Amount of input tokens borrowed in this market using variable interest rates (in native terms) "
  variableBorrowedTokenBalance: BigInt

  " Amount of input tokens borrowed in this market using stable interest rates (in native terms) "
  stableBorrowedTokenBalance: BigInt

  " Allowed limit to how much of the underlying asset can be supplied to this market. "
  supplyCap: BigInt

  " Allowed limit for how much of the underlying asset can be borrowed from this market. "
  borrowCap: BigInt

  " Current TVL (Total Value Locked) of this market "
  totalValueLockedUSD: BigDecimal!

  " All revenue generated by the market, accrued to the supply side. "
  cumulativeSupplySideRevenueUSD: BigDecimal!

  " Daily revenue generated by the market, accrued to the supply side. "
  dailySupplySideRevenueUSD: BigDecimal!

  " All revenue generated by the market, accrued to the protocol. "
  cumulativeProtocolSideRevenueUSD: BigDecimal!

  " Daily revenue generated by the market, accrued to the protocol. "
  dailyProtocolSideRevenueUSD: BigDecimal!

  " All revenue generated by the market. "
  cumulativeTotalRevenueUSD: BigDecimal!

  " Daily revenue generated by the market. "
  dailyTotalRevenueUSD: BigDecimal!

  " Details of revenue sources and amounts "
  revenueDetail: RevenueDetail

  " Current balance of all deposited assets (not historical cumulative), in USD. Same as pool TVL. "
  totalDepositBalanceUSD: BigDecimal!

  " Sum of all deposits made on a given day, in USD "
  dailyDepositUSD: BigDecimal!

  " Sum of all the deposits on a given day, in native units "
  dailyNativeDeposit: BigInt!

  " Sum of all historical deposits in USD (only considers deposits and not withdrawals) "
  cumulativeDepositUSD: BigDecimal!

  " Current balance of all borrowed/minted assets (not historical cumulative), in USD. "
  totalBorrowBalanceUSD: BigDecimal!

  " Sum of all borrows/mints made on a given day, in USD "
  dailyBorrowUSD: BigDecimal!

  " Sum of all the borrows on a given day, in native units "
  dailyNativeBorrow: BigInt!

  " Sum of all historical borrows/mints in USD (i.e. total loan origination) "
  cumulativeBorrowUSD: BigDecimal!

  " Total assets liquidated on a given day, in USD. "
  dailyLiquidateUSD: BigDecimal!

  " Total assets liquidated on a given day, in native units. "
  dailyNativeLiquidate: BigInt!

  " Sum of all historical liquidations in USD "
  cumulativeLiquidateUSD: BigDecimal!

  " Total assets withdrawn on a given day, in USD. "
  dailyWithdrawUSD: BigDecimal!

  " Total assets withdrawn on a given day, in native units. "
  dailyNativeWithdraw: BigInt!

  " Total assets repaid on a given day, in USD. "
  dailyRepayUSD: BigDecimal!

  " Total assets repaid on a given day, in native units. "
  dailyNativeRepay: BigInt!

  " Total assets transferred on a given day, in USD. "
  dailyTransferUSD: BigDecimal!

  " Total assets transferred on a given day, in native units. "
  dailyNativeTransfer: BigInt!

  " Sum of all historical transfers in USD "
  cumulativeTransferUSD: BigDecimal!

  " Total assets flashloaned on a given day, in USD. "
  dailyFlashloanUSD: BigDecimal!

  " Total assets flashloaned on a given day, in native units. "
  dailyNativeFlashloan: BigInt!

  " Sum of all historical flashloans in USD "
  cumulativeFlashloanUSD: BigDecimal!

  ##### Usage Data #####

  " Number of unique daily active users. e.g. accounts that spent gas to interact with this market "
  dailyActiveUsers: Int!

  " Number of unique daily depositors "
  dailyActiveDepositors: Int!

  " Number of unique daily borrowers "
  dailyActiveBorrowers: Int!

  " Number of unique daily liquidators (accounts that performed liquidation) "
  dailyActiveLiquidators: Int!

  " Number of unique daily liquidatees (accounts that got liquidated) "
  dailyActiveLiquidatees: Int!

  " Number of unique daily transferrers (the sender in a Transfer) "
  dailyActiveTransferrers: Int!

  " Number of unique daily accounts that executed a flash loan"
  dailyActiveFlashloaners: Int!

  " Total number of deposits in a day "
  dailyDepositCount: Int!

  " Total number of withdrawals in a day "
  dailyWithdrawCount: Int!

  " Total number of borrows/mints in a day "
  dailyBorrowCount: Int!

  " Total number of repayments/burns in a day "
  dailyRepayCount: Int!

  " Total number of liquidations in a day "
  dailyLiquidateCount: Int!

  " Total number of transfers in a day "
  dailyTransferCount: Int!

  " Total number of flashloans in a day "
  dailyFlashloanCount: Int!

  ##### Account/Position Data #####

  " Number of positions in this market "
  positionCount: Int!

  " Number of open positions in this market "
  openPositionCount: Int!

  " Number of closed positions in this market "
  closedPositionCount: Int!

  " Number of lending positions in this market. Note: this is cumulative and strictly increasing "
  lendingPositionCount: Int!

  " Total number of lending positions touched in a day. This includes opening, closing, and modifying positions. "
  dailyActiveLendingPositionCount: Int!

  " Number of borrowing positions in this market. Note: this is cumulative and strictly increasing "
  borrowingPositionCount: Int!

  " Total number of borrow positions touched in a day. This includes opening, closing, and modifying positions. "
  dailyActiveBorrowingPositionCount: Int!
}

type MarketHourlySnapshot @entity @hourlySnapshot {
  " { Smart contract address of the market }{ # of hours since Unix epoch time } "
  id: Bytes!

  " Number of hours since Unix epoch time "
  hours: Int!

  " The protocol this snapshot belongs to "
  protocol: LendingProtocol!

  " The pool this snapshot belongs to "
  market: Market!

  " Block number of this snapshot "
  blockNumber: BigInt!

  " Timestamp of this snapshot "
  timestamp: BigInt!

  " A unique identifier that can relate multiple markets together. e.g. a common address that they all share. This is useful for markets with multiple input tokens "
  relation: Bytes

  ##### Incentives #####

  " Additional tokens that are given as reward for position in a protocol, usually in liquidity mining programs. e.g. SUSHI in the Onsen program, MATIC for Aave Polygon "
  rewardTokens: [RewardToken!]

  " Per-block reward token emission as of the current block normalized to a day, in token's native amount. This should be ideally calculated as the theoretical rate instead of the realized amount. "
  rewardTokenEmissionsAmount: [BigInt!]

  " Per-block reward token emission as of the current block normalized to a day, in USD value. This should be ideally calculated as the theoretical rate instead of the realized amount. "
  rewardTokenEmissionsUSD: [BigDecimal!]

  " Total supply of output tokens that are staked. Used to calculate reward APY. "
  stakedOutputTokenAmount: BigInt

  ##### Quantitative Data #####

  " Amount of input token in the market (same order as inputTokens) "
  inputTokenBalance: BigInt!

  " Prices in USD of the input token (same order as inputTokens) "
  inputTokenPriceUSD: BigDecimal!

  " Total supply of output token (same order as outputTokens) "
  outputTokenSupply: BigInt

  " Prices in USD of the output token (same order as outputTokens) "
  outputTokenPriceUSD: BigDecimal

  " Amount of input token per full share of output token. Only applies when the output token exists (note this is a ratio and not a percentage value, i.e. 1.05 instead of 105%) "
  exchangeRate: BigDecimal

  " All interest rates for this input token. Should be in APR format "
  rates: [InterestRate!]

  " Total amount of reserves (in USD) "
  reserves: BigDecimal

  " Amount of input tokens borrowed in this market using variable interest rates (in native terms) "
  variableBorrowedTokenBalance: BigInt

  " Amount of input tokens borrowed in this market using stable interest rates (in native terms) "
  stableBorrowedTokenBalance: BigInt

  " Current TVL (Total Value Locked) of this market "
  totalValueLockedUSD: BigDecimal!

  " All revenue generated by the market, accrued to the supply side. "
  cumulativeSupplySideRevenueUSD: BigDecimal!

  " Hourly revenue generated by the market, accrued to the supply side. "
  hourlySupplySideRevenueUSD: BigDecimal!

  " All revenue generated by the market, accrued to the protocol. "
  cumulativeProtocolSideRevenueUSD: BigDecimal!

  " Hourly revenue generated by the market, accrued to the protocol. "
  hourlyProtocolSideRevenueUSD: BigDecimal!

  " All revenue generated by the market. "
  cumulativeTotalRevenueUSD: BigDecimal!

  " Hourly revenue generated by the market. "
  hourlyTotalRevenueUSD: BigDecimal!

  " Current balance of all deposited assets (not historical cumulative), in USD. Same as pool TVL. "
  totalDepositBalanceUSD: BigDecimal!

  " Sum of all deposits made in a given hour, in USD "
  hourlyDepositUSD: BigDecimal!

  " Sum of all historical deposits in USD (only considers deposits and not withdrawals) "
  cumulativeDepositUSD: BigDecimal!

  " Current balance of all borrowed/minted assets (not historical cumulative), in USD. "
  totalBorrowBalanceUSD: BigDecimal!

  " Sum of all borrows/mints made in a given hour, in USD "
  hourlyBorrowUSD: BigDecimal!

  " Sum of all historical borrows/mints in USD (i.e. total loan origination) "
  cumulativeBorrowUSD: BigDecimal!

  " Total assets liquidated in a given hour, in USD. "
  hourlyLiquidateUSD: BigDecimal!

  " Sum of all historical liquidations in USD "
  cumulativeLiquidateUSD: BigDecimal!

  " Total assets withdrawn on a given hour, in USD. "
  hourlyWithdrawUSD: BigDecimal!

  " Total assets repaid on a given hour, in USD. "
  hourlyRepayUSD: BigDecimal!

  " Total assets transferred on a given hour, in USD. "
  hourlyTransferUSD: BigDecimal!

  " Total assets flashloaned on a given hour, in USD. "
  hourlyFlashloanUSD: BigDecimal!
}

##############################
##### Account-Level Data #####
##############################

type Account @entity @regularPolling {
  " { Account address } "
  id: Bytes!

  " Number of positions this account has "
  positionCount: Int!

  " All positions that belong to this account "
  positions: [Position!]! @derivedFrom(field: "account")

  " Number of open positions this account has "
  openPositionCount: Int!

  " Number of closed positions this account has "
  closedPositionCount: Int!

  " Number of deposits this account made "
  depositCount: Int!

  " All deposit events of this account "
  deposits: [Deposit!]! @derivedFrom(field: "account")

  " Number of withdrawals this account made "
  withdrawCount: Int!

  " All withdraw events of this account "
  withdraws: [Withdraw!]! @derivedFrom(field: "account")

  " Number of borrows this account made "
  borrowCount: Int!

  " All borrow events of this account "
  borrows: [Borrow!]! @derivedFrom(field: "account")

  " Number of repays this account made "
  repayCount: Int!

  " All repay events of this account "
  repays: [Repay!]! @derivedFrom(field: "account")

  " Number of times this account liquidated a position "
  liquidateCount: Int!

  " All liquidation events where this account was the liquidator "
  liquidates: [Liquidate!]! @derivedFrom(field: "liquidator")

  " Number of times this account has been liquidated "
  liquidationCount: Int!

  " All liquidation events where this account got liquidated "
  liquidations: [Liquidate!]! @derivedFrom(field: "liquidatee")

  " Number of times this account has transferred "
  transferredCount: Int!

  " All transfer events where this account was the sender "
  transfers: [Transfer!]! @derivedFrom(field: "sender")

  " Number of times this account has received a transfer "
  receivedCount: Int!

  " All transfer events where this account was the receiver "
  receives: [Transfer!]! @derivedFrom(field: "receiver")

  " Number of times this account has executed a flashloan "
  flashloanCount: Int!

  " All flashloan events where this account executed it "
  flashloans: [Flashloan!]! @derivedFrom(field: "account")

  " The amount of rewards claimed by this account in USD (use the USD value at the time of claiming) "
  rewardsClaimedUSD: BigDecimal
}

# A position is defined as who has control over the collateral or debt
type Position @entity @regularPolling {
  " { Account address }-{ Market address }-{ Position Side }-{ Optional: Interest Rate Type}-{ Counter } "
  id: ID!

  " Account that owns this position "
  account: Account!

  " The market in which this position was opened "
  market: Market!

  " The asset in which this position was opened with "
  asset: Token!

  " The hash of the transaction that opened this position "
  hashOpened: Bytes!

  " The hash of the transaction that closed this position "
  hashClosed: Bytes

  " Block number of when the position was opened "
  blockNumberOpened: BigInt!

  " Timestamp when the position was opened "
  timestampOpened: BigInt!

  " Block number of when the position was closed (0 if still open) "
  blockNumberClosed: BigInt

  " Timestamp when the position was closed (0 if still open) "
  timestampClosed: BigInt

  " Side of the position (either lender or borrower) "
  side: PositionSide!

  " Type of interest rate used for this position (stable or variable). Generally for borrow side positions."
  type: InterestRateType

  " Whether this position has been enabled as a collateral (only applies to LENDER positions). For protocols (e.g. MakerDAO) that doesn't require enabling explicitly, this will always be true. "
  isCollateral: Boolean

  " Whether this position is being isolated from risk from other positions (only applies to LENDER positions). For protocols (e.g. Aave V3) this reduces risk exposure from other user positions. "
  isIsolated: Boolean

  " Token balance in this position, in native amounts "
  balance: BigInt!

  " The token balance of this position without interest generated (Used to calculate interest generated on a position) "
  principal: BigInt

  " Number of deposits related to this position "
  depositCount: Int!

  " All deposit events of this position "
  deposits: [Deposit!]! @derivedFrom(field: "position")

  " Number of withdrawals related to this position "
  withdrawCount: Int!

  " All withdraw events of this position "
  withdraws: [Withdraw!]! @derivedFrom(field: "position")

  " Number of borrows related to this position "
  borrowCount: Int!

  " All borrow events of this position "
  borrows: [Borrow!]! @derivedFrom(field: "position")

  " Number of repays related to this position "
  repayCount: Int!

  " All repay events of this position "
  repays: [Repay!]! @derivedFrom(field: "position")

  " Number of liquidations related to this position (incremented when this position is liquidated) "
  liquidationCount: Int!

  " Liquidation event related to this position (if exists) "
  liquidations: [Liquidate!]! @derivedFrom(field: "positions")

  " Number of times this position has transferred "
  transferredCount: Int!

  " Number of times this position has received a transfer "
  receivedCount: Int!

  " All transfer events related to this position "
  transfers: [Transfer!]! @derivedFrom(field: "positions")

  " Position daily snapshots for open positions "
  snapshots: [PositionSnapshot!]! @derivedFrom(field: "position")
}

# Unlike other snapshots that are taken at a fixed time interval. Position
# snapshots should be taken after every event, including the opening and
# closing events. This will prevent an ever growing number of snapshots
# for positions that are not moving. As we are only recording the balance
# in token amounts instead of in USD, this will work well.
# Note that we only take snapshot for open positions.
type PositionSnapshot @entity(immutable: true) @hourlySnapshot {
  " { Position ID }-{ Transaction hash }-{ Log index } "
  id: ID!

  " Transaction hash of the transaction that triggered this snapshot "
  hash: Bytes!

  " Event log index. For transactions that don't emit event, create arbitrary index starting from 0 "
  logIndex: Int!

  " Nonce of the transaction that triggered this snapshot "
  nonce: BigInt!

  " Account that owns this position "
  account: Account!

  " Position of this snapshot "
  position: Position!

  " Token balance in this position, in native amounts "
  balance: BigInt!

  " Token balance in this position, in USD "
  balanceUSD: BigDecimal!

  " Block number of this snapshot "
  blockNumber: BigInt!

  " Timestamp of this snapshot "
  timestamp: BigInt!

  ##### Interest Tracking Fields #####

  " The principal value without interest accrued. Used to calculate interest per position. "
  principal: BigInt

  " Base borrow OR supply index (based on the position side). Used to calculate interest across snapshots. "
  index: BigInt
}

# Helper entity for calculating daily/hourly active users
type _ActiveAccount @entity(immutable: true) {
  " { daily/hourly }-{ Address of the account }-{ Optional: Transaction Type }-{ Optional: Market Address }-{ Optional: Days/hours since Unix epoch } "
  id: ID!
}

# Helper entity for getting positions
type _PositionCounter @entity {
  " { Account address }-{ Market address }-{ Position Side } "
  id: ID!

  " Next count "
  nextCount: Int!

  " The last timestamp this position was updated "
  lastTimestamp: BigInt!
}

############################
##### Event-Level Data #####
############################

interface Event {
  " { Transaction hash }{ Log index } "
  id: Bytes!

  " Transaction hash of the transaction that emitted this event "
  hash: Bytes!

  " Nonce of the transaction that emitted this event "
  nonce: BigInt!

  " Event log index. For transactions that don't emit event, create arbitrary index starting from 0 "
  logIndex: Int!

  " Price of gas in this transaction "
  gasPrice: BigInt

  " Gas used in this transaction. (Optional because not every chain will support this) "
  gasUsed: BigInt

  " Gas limit of this transaction. e.g. the amount of gas the sender will pay "
  gasLimit: BigInt

  " Block number of this event "
  blockNumber: BigInt!

  " Timestamp of this event "
  timestamp: BigInt!

  " The market tokens are deposited to "
  market: Market!

  " Token deposited "
  asset: Token!

  " Amount of token deposited in native units "
  amount: BigInt!

  " Amount of token deposited in USD "
  amountUSD: BigDecimal!
}

type Deposit implements Event @entity(immutable: true) @transaction {
  " { Transaction hash }{ Log index } "
  id: Bytes!

  " Transaction hash of the transaction that emitted this event "
  hash: Bytes!

  " Nonce of the transaction that emitted this event "
  nonce: BigInt!

  " Event log index. For transactions that don't emit event, create arbitrary index starting from 0 "
  logIndex: Int!

  " Price of gas in this transaction "
  gasPrice: BigInt

  " Gas used in this transaction. (Optional because not every chain will support this) "
  gasUsed: BigInt

  " Gas limit of this transaction. e.g. the amount of gas the sender will pay "
  gasLimit: BigInt

  " Block number of this event "
  blockNumber: BigInt!

  " Timestamp of this event "
  timestamp: BigInt!

  "Account where deposit was executed (e.g. a deposit on behalf of account)"
  account: Account!

  " Account that executed the deposit (e.g. a deposit on behalf of account) "
  accountActor: Account

  " The market tokens are deposited to "
  market: Market!

  " The user position changed by this event "
  position: Position!

  " Token deposited "
  asset: Token!

  " Amount of token deposited in native units "
  amount: BigInt!

  " Amount of token deposited in USD "
  amountUSD: BigDecimal!
}

type Withdraw implements Event @entity(immutable: true) @transaction {
  " { Transaction hash }{ Log index } "
  id: Bytes!

  " Transaction hash of the transaction that emitted this event "
  hash: Bytes!

  " Nonce of the transaction that emitted this event "
  nonce: BigInt!

  " Event log index. For transactions that don't emit event, create arbitrary index starting from 0 "
  logIndex: Int!

  " Price of gas in this transaction "
  gasPrice: BigInt

  " Gas used in this transaction. (Optional because not every chain will support this) "
  gasUsed: BigInt

  " Gas limit of this transaction. e.g. the amount of gas the sender will pay "
  gasLimit: BigInt

  " Block number of this event "
  blockNumber: BigInt!

  " Timestamp of this event "
  timestamp: BigInt!

  " Account that controls the position (e.g. the aToken owner initiating the withdraw in Aave) "
  account: Account!

  " Account that receives the underlying withdrawn amount "
  accountActor: Account

  " The market tokens are withdrew from "
  market: Market!

  " The user position changed by this event "
  position: Position!

  " Token withdrawn "
  asset: Token!

  # Certain protocols (e.g. MakerDAO) uses a negative amount for withdraws. You
  # should convert them to positive for consistency.
  # e.g. Event log 27 in https://etherscan.io/tx/0xe957cf6252c7712c218c842c1ade672bf5ce529f8512f7a5ce7ebc8afa4ec690#eventlog

  " Amount of token withdrawn in native units "
  amount: BigInt!

  " Amount of token withdrawn in USD "
  amountUSD: BigDecimal!
}

# For CDPs, use this for mint events
type Borrow implements Event @entity(immutable: true) @transaction {
  " { Transaction hash }{ Log index } "
  id: Bytes!

  " Transaction hash of the transaction that emitted this event "
  hash: Bytes!

  " Nonce of the transaction that emitted this event "
  nonce: BigInt!

  " Event log index. For transactions that don't emit event, create arbitrary index starting from 0 "
  logIndex: Int!

  " Price of gas in this transaction "
  gasPrice: BigInt

  " Gas used in this transaction. (Optional because not every chain will support this) "
  gasUsed: BigInt

  " Gas limit of this transaction. e.g. the amount of gas the sender will pay "
  gasLimit: BigInt

  " Block number of this event "
  blockNumber: BigInt!

  " Timestamp of this event "
  timestamp: BigInt!

  " Account that controls incurs debt in this transaction "
  account: Account!

  " Account that receives the funds from the new debt "
  accountActor: Account

  " The market tokens are borrowed/minted from "
  market: Market!

  " The user position changed by this event "
  position: Position!

  " Token borrowed "
  asset: Token!

  " Amount of token borrowed in native units "
  amount: BigInt!

  " Amount of token borrowed in USD "
  amountUSD: BigDecimal!
}

# For CDPs, use this for burn events
type Repay implements Event @entity(immutable: true) @transaction {
  " { Transaction hash }{ Log index } "
  id: Bytes!

  " Transaction hash of the transaction that emitted this event "
  hash: Bytes!

  " Nonce of the transaction that emitted this event "
  nonce: BigInt!

  " Event log index. For transactions that don't emit event, create arbitrary index starting from 0 "
  logIndex: Int!

  " Price of gas in this transaction "
  gasPrice: BigInt

  " Gas used in this transaction. (Optional because not every chain will support this) "
  gasUsed: BigInt

  " Gas limit of this transaction. e.g. the amount of gas the sender will pay "
  gasLimit: BigInt

  " Block number of this event "
  blockNumber: BigInt!

  " Timestamp of this event "
  timestamp: BigInt!

  " Account that reduces their debt on this transaction "
  account: Account!

  " Account that is providing the funds to repay the debt "
  accountActor: Account

  " The market tokens are repaid/burned to "
  market: Market!

  " The user position changed by this event "
  position: Position!

  " Token repaid/burned "
  asset: Token!

  " Amount of token repaid/burned in native units "
  amount: BigInt!

  " Amount of token repaid/burned in USD "
  amountUSD: BigDecimal!
}

type Liquidate implements Event @entity(immutable: true) @transaction {
  " { Transaction hash }{ Log index } "
  id: Bytes!

  " Transaction hash of the transaction that emitted this event "
  hash: Bytes!

  " Nonce of the transaction that emitted this event "
  nonce: BigInt!

  " Event log index. For transactions that don't emit event, create arbitrary index starting from 0 "
  logIndex: Int!

  " Price of gas in this transaction "
  gasPrice: BigInt

  " Gas used in this transaction. (Optional because not every chain will support this) "
  gasUsed: BigInt

  " Gas limit of this transaction. e.g. the amount of gas the sender will pay "
  gasLimit: BigInt

  " Block number of this event "
  blockNumber: BigInt!

  " Timestamp of this event "
  timestamp: BigInt!

  " Account that carried out the liquidation "
  liquidator: Account!

  " Account that got liquidated "
  liquidatee: Account!

  " The market of the collateral being used "
  market: Market!

  " The user position changed by this event "
  positions: [Position!]!

  " Asset repaid (borrowed) "
  asset: Token!

  " Amount of collateral liquidated in native units "
  amount: BigInt!

  " Amount of collateral liquidated in USD "
  amountUSD: BigDecimal!

  " Amount of profit from liquidation in USD "
  profitUSD: BigDecimal!
}

# This entity is solely for transfers outside of normal protocol interaction
# e.g. transferring aTokens (collateral) directly, not a deposit.
# Transfers associated with other transactions in this schema should live there and not here.
# Note that only one transfer event should be created per transfer.
type Transfer implements Event @entity(immutable: true) @transaction {
  " { Transaction hash }{ Log index } "
  id: Bytes!

  " Transaction hash of the transaction that emitted this event "
  hash: Bytes!

  " Nonce of the transaction that emitted this event "
  nonce: BigInt!

  " Event log index. For transactions that don't emit event, create arbitrary index starting from 0 "
  logIndex: Int!

  " Price of gas in this transaction "
  gasPrice: BigInt

  " Gas used in this transaction. (Optional because not every chain will support this) "
  gasUsed: BigInt

  " Gas limit of this transaction. e.g. the amount of gas the sender will pay "
  gasLimit: BigInt

  " Block number of this event "
  blockNumber: BigInt!

  " Timestamp of this event "
  timestamp: BigInt!

  " The account that sent the tokens "
  sender: Account!

  " The Account that received the tokens "
  receiver: Account!

  " The user positions changed by this event "
  positions: [Position!]!

  " The market associated with the token transfer "
  market: Market!

  " The asset that was actually transferred. This could also include a debt token. "
  asset: Token!

  " Amount of token transferred in native units "
  amount: BigInt!

  " Amount of token transferred in USD "
  amountUSD: BigDecimal!
}

type Flashloan implements Event @entity(immutable: true) @transaction {
  " { Transaction hash }{ Log index } "
  id: Bytes!

  " Transaction hash of the transaction that emitted this event "
  hash: Bytes!

  " Nonce of the transaction that emitted this event "
  nonce: BigInt!

  " Event log index. For transactions that don't emit event, create arbitrary index starting from 0 "
  logIndex: Int!

  " Price of gas in this transaction "
  gasPrice: BigInt

  " Gas used in this transaction. (Optional because not every chain will support this) "
  gasUsed: BigInt

  " Gas limit of this transaction. e.g. the amount of gas the sender will pay "
  gasLimit: BigInt

  " Block number of this event "
  blockNumber: BigInt!

  " Timestamp of this event "
  timestamp: BigInt!

  " Account that receives the funds from the flashloan "
  account: Account!

  " Account that initiates the flashloan "
  accountActor: Account

  " The market in which this flashloan is executed "
  market: Market!

  " Asset borrowed "
  asset: Token!

  " Amount of asset borrowed in native units "
  amount: BigInt!

  " Amount of asset borrowed in USD "
  amountUSD: BigDecimal!

  " Amount of asset taken by protocol as a fee in native units "
  feeAmount: BigInt

  " Amount of asset taken by protocol as a fee in USD "
  feeAmountUSD: BigDecimal
}
"""

# def ask_gpt4(question, context):
#     # url = "https://api.openai.com/v1/chat/completions/"

#     api_key = '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'
#     headers = {
#         'Content-Type': 'application/json',
#         'Authorization': f'Bearer {api_key}',
#     }
#     response = openai.Completion.create(
#     engine="text-davinci-002",
#     prompt=f"{text}\n\n{question}",
#     temperature=0.5,
#     max_tokens=100
# ) 
#     # Define the body of the API request
#     body = {
#         "prompt": "your_prompt",
#         "max_tokens": 100,  # Modify as needed
#         "temperature": 0.7,  # Modify as needed
#         "top_p": 1,  # Modify as needed
#     }

#     # Send the API request and get the response
#     response = requests.post(url, headers=headers, data=json.dumps(body))
#     response_json = response.json()
#     print(response_json)
#     # response = requests.post('https://api.openai.com/v4/engines/gpt-4', headers=headers, json=data)
#     # print(response)
#     # response_json = response.json()
#     # return response_json['choices'][0]['text'].strip()

# Example usage:
question = """
You are an AI that helps write GraphQL queries on the Graph Protocol.
In the coming prompts I'll feed you questions that you need to turn into graphQL queries that work.
Note that it's important that if you don't have some specific data (like dates or IDs), just add placeholders.
Show only code and do not use sentences.

Write the GraphQL for the lending subgraph to pull data for the past day for following fields:

APY
TVL
APR
Volume
Transactions # count
# of unique depositors
sum of deposit amounts
# of unique borrowers
# of deposits
# of borrows
Sum of borrow amounts

The schema is defined as:
{}
# """
# context = schema
# print(ask_gpt4(question, context))


PRE_PROMPT = """
You are an AI that helps write GraphQL queries on the Graph Protocol.
In the coming prompts I'll feed you questions that you need to turn into graphQL queries that work.
Note that it's important that if you don't have some specific data (like dates or IDs), just add placeholders.
Show only code and do not use sentences.

Pull the following fields:

APY
TVL
APR
Volume
Transactions # count
# of unique depositors
sum of deposit amounts
# of unique borrowers
# of deposits
# of borrows
Sum of borrow amounts

The schema is defined as:
{}"""


# llm_predictor = LLMPredictor(
#             llm=OpenAI(temperature=0, model_name="text-davinci-003")
#         )
# # set maximum input size
# max_input_size = 4096
# # set number of output tokens
# num_output = 256
# # set maximum chunk overlap
# max_chunk_overlap = 20
# prompt_helper = PromptHelper(max_input_size, num_output, max_chunk_overlap)

# index = GPTSimpleVectorIndex(
#     documents, llm_predictor=llm_predictor, prompt_helper=prompt_helper
# )


import json
import requests
from graphql import build_schema, introspection_from_schema

def load_schema(file_name):
    with open(file_name, 'r') as file:
        schema_sdl = file.read()
        schema = build_schema(schema_sdl)
        introspection = introspection_from_schema(schema)
    return introspection

def generate_query_question(schema):
    # Here we'll generate a basic question about querying the first field in the schema
    # This is a naive approach, you might want to refine this according to your needs
    first_field = list(schema.keys())[0]
    return f"How can I query the data using the field '{first_field}'?"

def ask_gpt(question, endpoint, headers, data):
    data['prompt'] = question
    response = requests.post(endpoint, headers=headers, json=data)
    
    if response.status_code == 200:
        return response.json()['choices'][0]['text']
    else:
        return f"Error: {response.status_code}"

# Load the schema
schema = load_schema("schema_lending_ex.graphql")

# Generate a question about the schema
question = generate_query_question(schema)
api_key = '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'

# GPT endpoint details
gpt_endpoint = "https://api.openai.com/v1/engines/davinci-codex/completions"
gpt_headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer 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"
}
gpt_data = {
    "max_tokens": 10000
}
question = """
You are an AI that helps write GraphQL queries on the Graph Protocol.
In the coming prompts I'll feed you questions that you need to turn into graphQL queries that work.
Note that it's important that if you don't have some specific data (like dates or IDs), just add placeholders.
Show only code and do not use sentences.

Write the GraphQL for the lending subgraph to pull data for the past day for following fields:

APY
TVL
APR
Volume
Transactions # count
# of unique depositors
sum of deposit amounts
# of unique borrowers
# of deposits
# of borrows
Sum of borrow amounts

The schema is defined as:
{}"""

# Ask GPT the question
answer = ask_gpt(question, gpt_endpoint, gpt_headers, gpt_data)

print(answer)

