"""One-off emitter for shared-base batch-142 — web3/crypto domain (rollups, DeFi, zk, wallets, oracles, indexers, bridges, MEV, cryptography).

Writes 50 rows to data/v2/shared/batch_142.tmp.jsonl with ids shared-07051..07100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_142.tmp.jsonl"
ID_OFFSET = 7050

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Routed the perps frontend from Arbitrum to Base for launch week; gas costs dropped far enough that grid-order bots stopped batching and quote refresh times tightened noticeably.", "decision", "technical", False,
     [("Arbitrum", "platform"), ("Base", "platform"), ("perps frontend", "project")],
     [("Base", "Arbitrum", "REPLACES"), ("perps frontend", "Base", "DEPLOYED_ON")],
     "which L2 did the perps frontend migrate to for launch and what bot behaviour shifted as a result",
     "arbitrum base perps frontend l2 migrate gas grid bot quote"),
    # --- 2 ---
    ("Swapped the Uniswap v2 router integration for the Uniswap v4 singleton with custom hooks; the dynamic fee hook gave us fee-on-volatility without deploying a fork of the router.", "decision", "technical", False,
     [("Uniswap v2", "protocol"), ("Uniswap v4", "protocol"), ("custom hooks", "pattern")],
     [("Uniswap v4", "Uniswap v2", "REPLACES"), ("Uniswap v4", "custom hooks", "USES")],
     "which AMM upgrade gave us dynamic fee logic without forking the router",
     "uniswap v4 v2 hook singleton dynamic fee router swap upgrade"),
    # --- 3 ---
    ("Lending vault now forwards idle USDC to Aave v3 on Base instead of Compound v3; the supply APY curve under light utilisation ended up consistently higher across a two-week sample.", "fact", "technical", False,
     [("USDC", "technology"), ("Aave v3", "protocol"), ("Compound v3", "protocol"), ("Base", "platform")],
     [("Aave v3", "Compound v3", "REPLACES"), ("Aave v3", "Base", "DEPLOYED_ON")],
     "which money-market venue does the lending vault now park idle USDC on and why did it win",
     "aave compound v3 usdc base lending vault idle supply apy"),
    # --- 4 ---
    ("Our zk prover pipeline ships with RISC Zero as the default and SP1 available behind a feature flag; both consume the same ELF so switching backends is a cargo flag, not a code change.", "architecture", "technical", False,
     [("RISC Zero", "framework"), ("SP1", "framework"), ("ELF", "technology")],
     [("RISC Zero", "ELF", "USES"), ("SP1", "ELF", "USES")],
     "how does the prover stack let us swap zkVM backends without touching guest code",
     "risc zero sp1 zkvm elf prover backend feature flag cargo"),
    # --- 5 ---
    ("Cross-chain messaging layer is LayerZero v2 with the Wormhole DVN in the verifier set; single-provider trust assumptions scared the security review so we split verification between two DVNs.", "architecture", "technical", False,
     [("LayerZero v2", "protocol"), ("Wormhole", "protocol"), ("DVN", "concept")],
     [("LayerZero v2", "Wormhole", "USES")],
     "which cross-chain stack do we run and how is the verifier set structured to avoid single-provider trust",
     "layerzero v2 wormhole dvn verifier cross chain message trust"),
    # --- 6 ---
    ("Price oracle consumption pulls Chainlink as the primary feed with a Pyth pull-based snapshot as the tiebreaker; staleness over 90 seconds fails the transaction before any swap settles.", "architecture", "technical", False,
     [("Chainlink", "service"), ("Pyth", "service"), ("staleness", "concept")],
     [("Chainlink", "Pyth", "RELATED_TO")],
     "how does the protocol combine oracle feeds and what staleness window aborts a swap",
     "chainlink pyth oracle feed stale tiebreaker swap abort price"),
    # --- 7 ---
    ("Indexing moved from The Graph hosted service to a self-hosted Ponder deployment on Railway; subgraph redeploy latency went from hours to minutes and we stopped eating query-cost overages.", "milestone", "technical", False,
     [("The Graph", "service"), ("Ponder", "framework"), ("Railway", "platform")],
     [("Ponder", "The Graph", "REPLACES"), ("Ponder", "Railway", "DEPLOYED_ON")],
     "which indexer swap cut subgraph redeploy latency and what hosting venue runs the new stack",
     "the graph ponder railway subgraph indexer self host redeploy"),
    # --- 8 ---
    ("Solidity contracts compile with Foundry now; Hardhat only survives as the TypeScript test harness for the frontend because Foundry fuzzing caught three reentrancy edge cases Hardhat missed.", "decision", "technical", False,
     [("Solidity", "language"), ("Foundry", "tool"), ("Hardhat", "framework"), ("reentrancy", "concept")],
     [("Foundry", "Hardhat", "REPLACES")],
     "which smart-contract toolchain replaced Hardhat for compilation and what bug class did fuzzing catch",
     "foundry hardhat solidity fuzz reentrancy toolchain compile test"),
    # --- 9 ---
    ("Account abstraction rollout landed ERC-4337 bundlers behind a Pimlico relay; gasless onboarding flows now pay through a paymaster keyed per-session so a compromised key can't drain the sponsor.", "milestone", "technical", False,
     [("ERC-4337", "protocol"), ("Pimlico", "service"), ("paymaster", "concept")],
     [("ERC-4337", "Pimlico", "USES")],
     "how does the account-abstraction rollout sponsor gas and what limits the blast radius of a key compromise",
     "erc 4337 pimlico paymaster account abstraction bundler gasless session"),
    # --- 10. noise ---
    ("The office coffee machine started grinding an extra fifteen seconds after someone recalibrated the hopper and nobody has dared to touch it since.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("MEV protection sits behind Flashbots Protect RPC in the wallet default; users sending swaps on mainnet stopped getting sandwiched after we flipped the default endpoint in WalletConnect sessions.", "architecture", "technical", False,
     [("Flashbots", "service"), ("Protect RPC", "service"), ("WalletConnect", "protocol")],
     [("Protect RPC", "WalletConnect", "CONFIGURES")],
     "which RPC default stops sandwich attacks on wallet swaps and where is it wired in",
     "flashbots protect rpc wallet connect sandwich mev default swap"),
    # --- 12 ---
    ("Settlement on the perps venue uses a Hyperliquid-style central limit order book rather than a constant-function AMM; the market maker program closes the spread tighter than any AMM curve we benchmarked.", "decision", "technical", False,
     [("Hyperliquid", "platform"), ("central limit order book", "pattern"), ("constant-function AMM", "pattern")],
     [("central limit order book", "constant-function AMM", "REPLACES")],
     "which matching engine did the perps venue pick over an AMM and what metric drove the decision",
     "hyperliquid clob amm perps matching spread market maker benchmark"),
    # --- 13 ---
    ("Restaking collateral flows through EigenLayer operators with a slashing guard: any operator with a drawdown above 2% in a week is auto-queued for undelegation before the next epoch.", "fact", "technical", False,
     [("EigenLayer", "protocol"), ("operator", "concept"), ("slashing", "concept")],
     [("EigenLayer", "slashing", "USES")],
     "how does the restaking flow auto-protect stakers when an EigenLayer operator underperforms",
     "eigenlayer operator slashing drawdown undelegate restake collateral"),
    # --- 14 ---
    ("Data availability is posted to Celestia for the rollup's sovereign chain rather than to Ethereum calldata; blob fees in the pre-Dencun era made Ethereum DA ten times more expensive per megabyte.", "decision", "technical", False,
     [("Celestia", "platform"), ("Ethereum", "platform"), ("rollup", "concept"), ("calldata", "concept")],
     [("Celestia", "Ethereum", "REPLACES"), ("rollup", "Celestia", "USES")],
     "which DA layer did the sovereign rollup pick over Ethereum calldata and what cost ratio drove it",
     "celestia ethereum data availability rollup calldata blob fee sovereign"),
    # --- 15 ---
    ("Bridge architecture retired the lock-and-mint model in favour of a CCTP-powered burn-and-mint for USDC; canonical representation removed the wrapped-asset fragmentation that plagued user support.", "architecture", "technical", False,
     [("CCTP", "protocol"), ("lock-and-mint", "pattern"), ("burn-and-mint", "pattern"), ("USDC", "technology")],
     [("burn-and-mint", "lock-and-mint", "REPLACES"), ("CCTP", "USDC", "APPLIES_TO")],
     "which bridge model replaced lock-and-mint for USDC and what user-facing pain did canonical transfer fix",
     "cctp burn mint lock usdc bridge canonical wrapped fragment"),
    # --- 16 ---
    ("Market-making bot on Drift was hitting RPC timeouts during volatile minutes; sharded a Helius account-subscribe websocket per market and the order-refresh p99 dropped back under 80 ms.", "problem", "technical", False,
     [("Drift", "platform"), ("Helius", "service"), ("account-subscribe", "api")],
     [("Helius", "Drift", "SUPPORTS")],
     "which RPC change cut order-refresh p99 latency for the Drift market maker during volatility",
     "drift helius rpc websocket market maker p99 refresh account"),
    # --- 17 ---
    ("Deployment targets for the staking contracts are Arbitrum, Optimism, and Base mainnets; Ethereum L1 only carries the governance timelock because L2 gas keeps the staker-rewards loop profitable at smaller positions.", "fact", "technical", False,
     [("Arbitrum", "platform"), ("Optimism", "platform"), ("Base", "platform"), ("Ethereum", "platform"), ("timelock", "concept")],
     [("timelock", "Ethereum", "DEPLOYED_ON")],
     "which chains host the staking contracts versus the governance timelock and why",
     "arbitrum optimism base ethereum staking timelock governance l2"),
    # --- 18 ---
    ("Proving stack for the zkEVM rollup picked Polygon CDK over zkSync's Stack for its Plonky2 recursion; benchmark proofs finished four times faster at the expense of a slightly larger final proof size.", "decision", "technical", False,
     [("Polygon CDK", "framework"), ("zkSync", "platform"), ("Plonky2", "algorithm"), ("zkEVM", "concept")],
     [("Polygon CDK", "Plonky2", "USES"), ("Polygon CDK", "zkSync", "PREFERS")],
     "which zk framework did the rollup choose over zkSync's stack and what speed tradeoff came with it",
     "polygon cdk plonky2 zksync zkevm rollup proof recursion speed"),
    # --- 19 ---
    ("Multichain Solana program deploys run through Anchor 0.30 with an IDL-emitted TypeScript client; the old hand-written borsh encoders kept drifting from the Rust layout on every instruction add.", "decision", "technical", False,
     [("Solana", "platform"), ("Anchor", "framework"), ("borsh", "library"), ("IDL", "concept")],
     [("Anchor", "borsh", "REPLACES"), ("Anchor", "IDL", "PRODUCES")],
     "which Solana framework replaced hand-written borsh encoders and what file does it emit for clients",
     "anchor solana borsh idl typescript client instruction drift"),
    # --- 20 ---
    ("Wallet signing UX migrated from eth_signTypedData_v3 to eth_signTypedData_v4 domains; the v3 path silently dropped nested struct types on Ledger devices, which corrupted EIP-712 permit signatures for half our iOS users.", "problem", "technical", False,
     [("eth_signTypedData_v3", "api"), ("eth_signTypedData_v4", "api"), ("Ledger", "technology"), ("EIP-712", "protocol")],
     [("eth_signTypedData_v4", "eth_signTypedData_v3", "REPLACES")],
     "which typed-data version fixed the Ledger nested-struct signing bug in EIP-712 permits",
     "eip 712 sign typed data v4 v3 ledger permit nested struct"),
    # --- 21 ---
    ("Integrated Tenderly simulation into the transaction preview card; users see token-flow diffs and expected revert reasons before confirming, which cut support tickets about failed swaps by a noticeable chunk.", "milestone", "technical", False,
     [("Tenderly", "service"), ("transaction preview", "pattern"), ("token-flow diff", "concept")],
     [("transaction preview", "Tenderly", "USES")],
     "which simulator powers the pre-confirm transaction preview and what support metric improved",
     "tenderly simulation transaction preview token flow revert support"),
    # --- 22 ---
    ("The DAO governance module uses OpenZeppelin Governor with a Tally frontend; Compound's Governor Bravo was considered but the Timelock upgrade path in OZ fit our multisig rotation plan better.", "decision", "technical", False,
     [("OpenZeppelin Governor", "library"), ("Tally", "service"), ("Governor Bravo", "protocol"), ("Timelock", "concept")],
     [("OpenZeppelin Governor", "Governor Bravo", "PREFERS"), ("OpenZeppelin Governor", "Tally", "COMMUNICATES_WITH")],
     "which governance contract stack did the DAO pick and why did Governor Bravo lose the comparison",
     "openzeppelin governor bravo tally dao timelock multisig governance"),
    # --- 23 ---
    ("Stable-swap pool for the LST trio uses a Curve-style invariant rather than Balancer weighted; the LST depeg that hit 60 bps last quarter cleared in a day thanks to the flatter bonding curve.", "architecture", "technical", False,
     [("Curve", "protocol"), ("Balancer", "protocol"), ("LST", "concept"), ("bonding curve", "concept")],
     [("Curve", "Balancer", "PREFERS"), ("Curve", "bonding curve", "USES")],
     "which AMM invariant does the LST trio pool run under and how did it absorb the recent depeg",
     "curve balancer lst depeg stable swap bonding invariant weighted"),
    # --- 24 ---
    ("Treasury diversification put stables into Maker's sDAI and Ethena's USDe in equal weight; leaving idle USDC in a Gnosis Safe felt wasteful once the DSR crossed 5%.", "fact", "technical", False,
     [("Maker", "protocol"), ("sDAI", "technology"), ("Ethena", "protocol"), ("USDe", "technology"), ("Gnosis Safe", "service")],
     [("sDAI", "Maker", "PRODUCES"), ("USDe", "Ethena", "PRODUCES")],
     "which yield-bearing stables did the treasury diversify into once idle USDC felt wasteful",
     "sdai maker ethena usde treasury gnosis safe yield diversify"),
    # --- 25 ---
    ("Proof-of-reserves attestations for the custody arm are signed with Merkle-sum trees rotated weekly; auditors previously accepted a flat snapshot, but that left no binding from each user's balance to the root.", "architecture", "technical", False,
     [("Proof-of-reserves", "concept"), ("Merkle-sum tree", "algorithm"), ("flat snapshot", "pattern")],
     [("Merkle-sum tree", "flat snapshot", "REPLACES")],
     "how does the custody arm attest reserves now and what binding was missing in the earlier snapshot approach",
     "proof reserves merkle sum tree custody snapshot root user"),
    # --- 26 ---
    ("Switched gas estimation from eth_estimateGas to a simulated state override via Alchemy; edge cases around token transfer hooks stopped under-estimating and users stopped seeing out-of-gas reverts on L1 swaps.", "fact", "technical", False,
     [("eth_estimateGas", "api"), ("Alchemy", "service"), ("state override", "pattern")],
     [("state override", "eth_estimateGas", "REPLACES")],
     "how did we stop under-estimating gas for token-hook swaps and which RPC provider powers the new path",
     "eth estimate gas alchemy state override hook under estimate revert"),
    # --- 27 ---
    ("NFT metadata is pinned on Filecoin via web3.storage and mirrored to Arweave bundlers; dual-pin eliminated the chance of link rot after a pinning gateway outage took out half our collection last summer.", "architecture", "technical", False,
     [("Filecoin", "platform"), ("web3.storage", "service"), ("Arweave", "platform")],
     [("web3.storage", "Filecoin", "DEPLOYED_ON"), ("Arweave", "web3.storage", "SUPPORTS")],
     "which dual-pin storage setup prevents NFT metadata rot when one gateway goes down",
     "filecoin web3 storage arweave nft metadata pin bundler gateway"),
    # --- 28 ---
    ("Monorepo consolidated the Ethers v5 and viem codepaths onto viem across every frontend; tree-shaken bundles shrank by about 40% and the typed contract-call API removed an entire class of address-type bugs.", "milestone", "technical", False,
     [("Ethers v5", "library"), ("viem", "library"), ("Monorepo", "pattern")],
     [("viem", "Ethers v5", "REPLACES")],
     "which Ethereum client library replaced Ethers v5 in the monorepo and what bundle win did it land",
     "viem ethers v5 monorepo bundle tree shake typed contract address"),
    # --- 29 ---
    ("IBC channel between the Cosmos app-chain and Neutron broke after a relayer packet-timeout burst; set minimum-gas-prices on Hermes relayer and reopened the channel after a governance re-init vote.", "problem", "technical", False,
     [("IBC", "protocol"), ("Cosmos", "platform"), ("Neutron", "platform"), ("Hermes", "tool")],
     [("IBC", "Cosmos", "DEPLOYED_ON"), ("Hermes", "IBC", "CONFIGURES")],
     "which config on the Hermes relayer unblocked the IBC channel between our Cosmos chain and Neutron",
     "ibc cosmos neutron hermes relayer packet timeout channel gas"),
    # --- 30 ---
    ("Private mempool submission for large orders routes through MEV-Share with partial hints; the hint schema hides the target token while still letting searchers backrun to recover gas rebates.", "reference", "technical", False,
     [("MEV-Share", "service"), ("mempool", "concept"), ("backrun", "pattern")],
     [("MEV-Share", "backrun", "SUPPORTS")],
     "how does the private mempool route hide order intent while still letting searchers backrun for rebates",
     "mev share private mempool hint backrun searcher rebate order"),
    # --- 31 ---
    ("zkSNARK circuits for the shielded transfer were re-written in Circom 2 with Groth16 as the proving system; the Halo2 prototype had lower-latency proofs but the ceremony requirement killed it for our launch window.", "decision", "technical", False,
     [("Circom", "language"), ("Groth16", "algorithm"), ("Halo2", "framework"), ("zkSNARK", "concept")],
     [("Groth16", "Halo2", "PREFERS")],
     "which proving system did we ship for shielded transfers and what practical concern killed Halo2",
     "circom groth16 halo2 zksnark shield transfer ceremony launch"),
    # --- 32 ---
    ("Staking receipt token wETH derivative migrated from Lido's wstETH wrapper to Renzo's ezETH; LRT exposure lined up with the points programme and the redeem window proved tighter under stress tests.", "decision", "technical", False,
     [("wstETH", "technology"), ("ezETH", "technology"), ("Lido", "protocol"), ("Renzo", "protocol")],
     [("ezETH", "wstETH", "REPLACES"), ("ezETH", "Renzo", "PRODUCES")],
     "which LST-to-LRT swap did the derivative book perform and which property tipped the decision",
     "lido renzo wsteth ezeth lst lrt stake derivative redeem"),
    # --- 33 ---
    ("Subgraph schema landed per-pool TVL snapshots keyed by day; the old per-event rollup rebuilt the whole timeline on every ingest and couldn't keep up with mainnet block times during NFT mint storms.", "reference", "technical", False,
     [("Subgraph", "concept"), ("TVL", "concept"), ("per-event rollup", "pattern")],
     [("Subgraph", "per-event rollup", "REPLACES")],
     "which TVL snapshotting change let the subgraph keep up with mainnet during mint storms",
     "subgraph tvl snapshot per event rollup day mint storm mainnet"),
    # --- 34 ---
    ("Hardware-wallet integration added Keystone QR-code signing alongside the existing Ledger HID path; air-gapped users can now sign without a USB cable and the signer adapter covers both with one interface.", "milestone", "technical", False,
     [("Keystone", "technology"), ("Ledger", "technology"), ("QR-code", "protocol"), ("signer adapter", "pattern")],
     [("signer adapter", "Keystone", "SUPPORTS"), ("signer adapter", "Ledger", "SUPPORTS")],
     "which second hardware-wallet flavour got added behind the signer adapter and what does the new flow require",
     "keystone ledger qr sign hardware wallet adapter air gapped"),
    # --- 35 ---
    ("Permit2 approvals replaced the per-token ERC-20 approve flow in our router; a single approval of Permit2 covers signature-based approvals per swap and users stopped accumulating unlimited allowances to random contracts.", "preference", "technical", False,
     [("Permit2", "protocol"), ("ERC-20", "protocol"), ("approve", "api"), ("router", "concept")],
     [("Permit2", "approve", "REPLACES")],
     "which approval scheme replaced per-token ERC-20 approvals in the router and what user risk did it reduce",
     "permit2 erc 20 approve router approval unlimited allowance sign"),
    # --- 36 ---
    ("Cross-chain swap aggregator compares CoW Swap, 1inch, and LI.FI routes in parallel then locks on whichever clears the quote gate; CoW wins on mainnet majors and LI.FI usually wins on L2-to-L2 small-cap routes.", "fact", "technical", False,
     [("CoW Swap", "protocol"), ("1inch", "protocol"), ("LI.FI", "service"), ("aggregator", "concept")],
     [("aggregator", "CoW Swap", "COMMUNICATES_WITH"), ("aggregator", "1inch", "COMMUNICATES_WITH"), ("aggregator", "LI.FI", "COMMUNICATES_WITH")],
     "which three route sources does the aggregator compare and where does each tend to win",
     "cow swap 1inch lifi aggregator route mainnet l2 small cap"),
    # --- 37 ---
    ("Rage-quit pattern on the multisig treasury uses Moloch v3 style proportional share redemption; a dissenting member can exit with their pro-rata stable share without blocking a proposal the majority supports.", "reference", "technical", False,
     [("Moloch v3", "protocol"), ("Rage-quit", "pattern"), ("multisig", "concept")],
     [("multisig", "Moloch v3", "USES")],
     "which DAO pattern lets a dissenting multisig member exit with a pro-rata share without blocking proposals",
     "moloch v3 rage quit multisig dao proportional share dissent"),
    # --- 38 ---
    ("Read the Ethereum Foundation's blob-fee design for EIP-4844 before pricing the rollup's DA budget; the target blob count of three per block caps the steady-state cost in a way that made our model tractable.", "reference", "technical", False,
     [("EIP-4844", "protocol"), ("Ethereum Foundation", "organization"), ("blob-fee", "concept")],
     [("EIP-4844", "blob-fee", "HAS_PART")],
     "which EIP spec describes the blob-fee mechanics we priced the rollup's DA budget against",
     "eip 4844 ethereum foundation blob fee rollup da budget target"),
    # --- 39 ---
    ("Circuit toolkit choice for the upcoming private voting module is Noir with Barretenberg as the backend; the DSL ergonomics beat Circom for our auditor and the UltraPlonk proofs verify cheaply on-chain.", "decision", "technical", False,
     [("Noir", "language"), ("Barretenberg", "framework"), ("Circom", "language"), ("UltraPlonk", "algorithm")],
     [("Noir", "Barretenberg", "USES"), ("Noir", "Circom", "PREFERS")],
     "which DSL and proving backend will the private-voting module use and what did it beat Circom on",
     "noir barretenberg circom ultraplonk private vote auditor dsl"),
    # --- 40 ---
    ("Cited Vitalik Buterin's post on endgame rollup-centric scaling when defending the L2 pivot to the board; the argument that L1 execution shrinks to settlement got us past the conservative voices.", "reference", "technical", False,
     [("Vitalik Buterin", "person"), ("rollup-centric scaling", "concept"), ("L1", "platform"), ("L2", "platform")],
     [("rollup-centric scaling", "Vitalik Buterin", "AUTHORED_BY")],
     "which essay framed the L2 pivot for the board and what core claim did it hang on",
     "vitalik buterin rollup centric scaling l1 l2 pivot board"),
    # --- 41 ---
    ("MEV-Boost is wired into the validator client by default on mainnet; solo stakers can opt out with a single flag, but the relay list was pruned down to three censorship-resistant operators after last year's OFAC incident.", "fact", "technical", False,
     [("MEV-Boost", "tool"), ("validator client", "concept"), ("OFAC", "organization"), ("relay", "concept")],
     [("MEV-Boost", "relay", "USES")],
     "how is MEV-Boost defaulted in the validator client and what pruning happened to the relay list",
     "mev boost validator relay ofac censor stake default prune"),
    # --- 42 ---
    ("Protocol fee routing sends 40% to the DAO treasury, 40% to staker rewards, and 20% to the insurance fund; the earlier 100%-to-stakers split starved the insurance fund after two liquidation cascades.", "decision", "technical", False,
     [("DAO treasury", "concept"), ("staker rewards", "concept"), ("insurance fund", "concept"), ("liquidation cascade", "concept")],
     [("staker rewards", "liquidation cascade", "CAUSES")],
     "how did the protocol fee split change after liquidation cascades exposed the insurance fund shortfall",
     "fee split dao treasury staker insurance fund liquidation cascade"),
    # --- 43. noise ---
    ("Somebody's plant on the south-facing windowsill finally bloomed after three years of patient watering and the whole floor got a group photo of it.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Spot-perps basis trade on dYdX migrated from the StarkEx-based v3 to the Cosmos-SDK v4; fills settle inside the chain's block instead of round-tripping to L1 and margin calls fire under 200 ms now.", "milestone", "technical", False,
     [("dYdX", "platform"), ("StarkEx", "framework"), ("Cosmos-SDK", "framework"), ("margin call", "concept")],
     [("Cosmos-SDK", "StarkEx", "REPLACES"), ("dYdX", "Cosmos-SDK", "USES")],
     "which settlement stack did dYdX shift the basis-trade venue onto and what latency number improved",
     "dydx v3 v4 starkex cosmos sdk basis trade margin call l1"),
    # --- 45 ---
    ("Solana validator fleet is split across Jito and vanilla Agave clients; the Jito-enabled nodes capture MEV tips for the stake pool while a third of the fleet stays vanilla to preserve client diversity.", "architecture", "technical", False,
     [("Solana", "platform"), ("Jito", "service"), ("Agave", "framework"), ("stake pool", "concept")],
     [("Jito", "Agave", "EXTENDS"), ("Jito", "stake pool", "SUPPORTS")],
     "how is the Solana validator fleet split between Jito and vanilla clients and what does each side do",
     "solana jito agave validator stake pool mev tip diversity"),
    # --- 46 ---
    ("Kept reading the Flashbots research on order-flow auctions; the suggestion to segment retail flow by user intent rather than by venue matches what we measured on our private RPC over six months.", "reference", "technical", False,
     [("Flashbots", "organization"), ("order-flow auction", "concept"), ("private RPC", "service")],
     [("order-flow auction", "Flashbots", "AUTHORED_BY")],
     "which Flashbots research thread shaped our retail flow segmentation and what metric matched it",
     "flashbots order flow auction retail segment intent rpc"),
    # --- 47 ---
    ("Stablecoin peg-defence bot runs on Starknet-native Cairo contracts; its Cairo 1 rewrite dropped proving time per cycle under the 12-second block target, so it finally reacts within the same slot the deviation appears.", "milestone", "technical", False,
     [("Starknet", "platform"), ("Cairo", "language"), ("Cairo 1", "language"), ("peg-defence bot", "project")],
     [("peg-defence bot", "Starknet", "DEPLOYED_ON"), ("Cairo 1", "Cairo", "REPLACES")],
     "which language migration let the peg-defence bot react within a Starknet slot and what was the block-time target",
     "starknet cairo 1 peg defence bot proving time slot block"),
    # --- 48 ---
    ("Simulation for the LTV parameter search uses Foundry's forked mainnet mode against a 30-day Anvil snapshot; iterating on the liquidation threshold without paying RPC costs saved a significant chunk of AWS spend.", "preference", "technical", False,
     [("Foundry", "tool"), ("Anvil", "tool"), ("LTV", "concept"), ("liquidation threshold", "concept")],
     [("Anvil", "Foundry", "HAS_PART"), ("LTV", "liquidation threshold", "RELATED_TO")],
     "how does the LTV parameter search iterate against mainnet state without paying live RPC costs",
     "foundry anvil ltv liquidation threshold fork mainnet snapshot rpc"),
    # --- 49 ---
    ("Prefer WalletConnect v2 over injected provider as the primary wallet connection path on mobile; deep-link return flows work reliably across iOS and the old injected path lost about one in five sessions on Safari in-app browsers.", "preference", "technical", False,
     [("WalletConnect v2", "protocol"), ("injected provider", "pattern"), ("Safari", "platform")],
     [("WalletConnect v2", "injected provider", "PREFERS")],
     "which mobile wallet-connection path do we prefer and what session-loss issue pushed us off the injected path",
     "walletconnect v2 inject provider safari mobile deep link session"),
    # --- 50 ---
    ("Keep token-list sources canonical through the Uniswap token list schema rather than curating a bespoke JSON; third-party consumers ingest our list without custom adapters and bad-actor additions get rejected by the existing validator set.", "preference", "technical", False,
     [("Uniswap token list", "protocol"), ("JSON", "technology"), ("validator", "concept")],
     [("Uniswap token list", "JSON", "REPLACES")],
     "which canonical format do we prefer for our token list source and what interoperability win came with it",
     "uniswap token list json schema canonical validator third party"),
]


def _find_span(text: str, needle: str, used: list[tuple[int, int]]) -> tuple[int, int]:
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            raise ValueError(f"entity name {needle!r} not found in text {text!r}")
        end = idx + len(needle)
        overlap = any(not (end <= s or idx >= e) for s, e in used)
        if not overlap:
            return idx, end
        start = idx + 1


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, entry in enumerate(ENTRIES, start=1):
            text, mt, domain, noise, ents, rels, qq, qk = entry
            used: list[tuple[int, int]] = []
            entities = []
            for name, typ in ents:
                s, e = _find_span(text, name, used)
                used.append((s, e))
                entities.append({"name": name, "type": typ, "start": s, "end": e})
            row: dict = {
                "id": f"shared-{ID_OFFSET + i:05d}",
                "domain": domain,
                "text": text,
                "memory_type": mt,
                "noise": noise,
                "entities": entities,
                "relationships": [{"source": s, "target": t, "type": r} for s, t, r in rels],
            }
            if qq is not None and qk is not None:
                row["queries"] = [
                    {"form": "question", "text": qq},
                    {"form": "keyword", "text": qk},
                ]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
