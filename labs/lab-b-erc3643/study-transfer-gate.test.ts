/**
 * Lab B. ERC-3643 토큰의 전송 게이트를 직접 열고 닫아 보기
 *
 * 기준 코드: github.com/ERC-3643/ERC-3643, 커밋 2f0704d (v4.1.3)
 * 위치: ERC-3643/test/study/study-transfer-gate.test.ts
 * 실행: npx hardhat test test/study/study-transfer-gate.test.ts
 *
 * 등장인물은 저장소의 deployFullSuiteFixture가 만들어 둔 그대로다.
 *   alice, bob : 신원(ONCHAINID) 등록 + 신뢰 발행자가 서명한 claim 보유 → 검증됨
 *   charlie    : 신원 컨트랙트는 있지만 레지스트리에 미등록, claim 없음
 *   another    : 아무것도 없음
 *   tokenAgent : 발행자 측 운영 주체 (pause, freeze, forcedTransfer 권한)
 *
 * Token.sol transfer() 417~426행의 검사 순서:
 *   whenNotPaused → 동결 여부 → 동결분 뺀 잔고 → isVerified(받는 쪽) && canTransfer → 전송
 */
import { loadFixture } from '@nomicfoundation/hardhat-network-helpers';
import { expect } from 'chai';
import { ethers } from 'hardhat';
import { deployFullSuiteFixture, deploySuiteWithModularCompliancesFixture } from '../fixtures/deploy-full-suite.fixture';

describe('Study - ERC-3643 transfer gate', () => {
  it('1. 검증된 사람끼리는 보통 ERC-20처럼 오간다', async () => {
    const {
      suite: { token },
      accounts: { aliceWallet, bobWallet },
    } = await loadFixture(deployFullSuiteFixture);

    await token.connect(aliceWallet).transfer(bobWallet.address, 100);
    expect(await token.balanceOf(bobWallet.address)).to.equal(600); // fixture에서 500을 받고 시작
  });

  it('2. 신원 등록만으로는 부족하다: 신뢰 발행자의 claim이 있어야 한다', async () => {
    const {
      suite: { token, identityRegistry, claimTopicsRegistry },
      accounts: { aliceWallet, charlieWallet, tokenAgent },
      identities: { charlieIdentity },
    } = await loadFixture(deployFullSuiteFixture);

    // 2-a. 레지스트리에 없으면 거절
    expect(await identityRegistry.isVerified(charlieWallet.address)).to.equal(false);
    await expect(token.connect(aliceWallet).transfer(charlieWallet.address, 100)).to.be.revertedWith('Transfer not possible');

    // 2-b. agent가 등록해도 claim이 없으면 여전히 거절 (국가 코드 410 = 대한민국, ISO-3166 숫자 코드)
    await identityRegistry.connect(tokenAgent).registerIdentity(charlieWallet.address, charlieIdentity.address, 410);
    expect(await identityRegistry.isVerified(charlieWallet.address)).to.equal(false);
    await expect(token.connect(aliceWallet).transfer(charlieWallet.address, 100)).to.be.revertedWith('Transfer not possible');

    // 2-c. 요구 claim topic을 전부 지우면(= KYC 요건을 없애면) 등록만으로 통과
    const topics = await claimTopicsRegistry.getClaimTopics();
    await Promise.all(topics.map((topic) => claimTopicsRegistry.removeClaimTopic(topic)));
    expect(await identityRegistry.isVerified(charlieWallet.address)).to.equal(true);
    await token.connect(aliceWallet).transfer(charlieWallet.address, 100);
    expect(await token.balanceOf(charlieWallet.address)).to.equal(100);
  });

  it('3. KYC 제공자를 신뢰 목록에서 빼면 이미 검증된 투자자도 받을 수 없게 된다', async () => {
    const {
      suite: { token, identityRegistry, claimTopicsRegistry, trustedIssuersRegistry },
      accounts: { aliceWallet, bobWallet },
    } = await loadFixture(deployFullSuiteFixture);

    const topics = await claimTopicsRegistry.getClaimTopics();
    const issuers = await trustedIssuersRegistry.getTrustedIssuersForClaimTopic(topics[0]);
    await Promise.all(issuers.map((issuer) => trustedIssuersRegistry.removeTrustedIssuer(issuer)));

    expect(await identityRegistry.isVerified(aliceWallet.address)).to.equal(false);
    await expect(token.connect(bobWallet).transfer(aliceWallet.address, 10)).to.be.revertedWith('Transfer not possible');
  });

  it('4. 발행자 측 통제: 일시정지와 지갑 동결', async () => {
    const {
      suite: { token },
      accounts: { aliceWallet, bobWallet, tokenAgent },
    } = await loadFixture(deployFullSuiteFixture);

    await token.connect(tokenAgent).setAddressFrozen(bobWallet.address, true);
    await expect(token.connect(aliceWallet).transfer(bobWallet.address, 100)).to.be.revertedWith('wallet is frozen');
    await token.connect(tokenAgent).setAddressFrozen(bobWallet.address, false);

    await token.connect(tokenAgent).pause();
    await expect(token.connect(aliceWallet).transfer(bobWallet.address, 100)).to.be.revertedWith('Pausable: paused');
  });

  it('5. forcedTransfer는 컴플라이언스 규칙은 건너뛰지만 받는 쪽 신원 검증은 건너뛰지 않는다', async () => {
    const {
      suite: { token, compliance },
      accounts: { aliceWallet, bobWallet, anotherWallet, tokenAgent },
    } = await loadFixture(deploySuiteWithModularCompliancesFixture);

    // 모든 전송을 막는 테스트용 모듈을 붙인다 (저장소의 token-transfer.test.ts와 같은 방법)
    const blocker = await ethers.deployContract('TestModule');
    await compliance.addModule(blocker.address);
    await token.setCompliance(compliance.address);
    const iface = new ethers.utils.Interface(['function blockModule(bool)']);
    await compliance.callModuleFunction(iface.encodeFunctionData('blockModule', [true]), blocker.address);

    // 일반 전송은 막힘
    await expect(token.connect(aliceWallet).transfer(bobWallet.address, 100)).to.be.revertedWith('Transfer not possible');

    // agent의 강제 이전은 통과 (법원 명령, 상속, 착오 송금 정정 같은 상황을 위한 기능)
    await token.connect(tokenAgent).forcedTransfer(aliceWallet.address, bobWallet.address, 100);
    expect(await token.balanceOf(bobWallet.address)).to.equal(600);

    // 그래도 검증 안 된 지갑으로는 강제 이전도 안 된다 (Token.sol 443행)
    await expect(token.connect(tokenAgent).forcedTransfer(aliceWallet.address, anotherWallet.address, 100)).to.be.revertedWith(
      'Transfer not possible',
    );
  });
});
