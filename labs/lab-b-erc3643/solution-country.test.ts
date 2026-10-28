/**
 * 10회차 과제 1 해설: ERC-3643 국가 제한 (contracts/compliance/legacy/features/CountryRestrictions.sol)
 * fixture에서 alice는 국가 코드 42, bob은 666으로 등록되어 있다. 666을 제한 국가로 지정해 본다.
 * 위치: ERC-3643/test/study/
 */
import { loadFixture } from '@nomicfoundation/hardhat-network-helpers';
import { expect } from 'chai';
import { ethers } from 'hardhat';
import { deployFullSuiteFixture } from '../fixtures/deploy-full-suite.fixture';

describe('Solution - country restriction', () => {
  it('제한 국가 거주자는 받을 수 없고, 보내는 것은 막지 않는다', async () => {
    const {
      suite: { token, identityRegistry },
      accounts: { aliceWallet, bobWallet },
    } = await loadFixture(deployFullSuiteFixture);

    expect(await identityRegistry.investorCountry(bobWallet.address)).to.equal(666);

    const compliance = await ethers.deployContract('CountryRestrictionsTest');
    await token.setCompliance(compliance.address);
    await compliance.addCountryRestriction(666);

    // 받는 쪽이 666이면 거절 (complianceCheckOnCountryRestrictions는 _to의 국가만 본다)
    await expect(token.connect(aliceWallet).transfer(bobWallet.address, 10)).to.be.revertedWith('Transfer not possible');
    // bob이 보내는 것은 통과 (받는 alice는 42)
    await token.connect(bobWallet).transfer(aliceWallet.address, 10);

    // 해제하면 다시 받을 수 있다
    await compliance.removeCountryRestriction(666);
    await token.connect(aliceWallet).transfer(bobWallet.address, 10);
    expect(await token.balanceOf(bobWallet.address)).to.equal(500);
  });

  it('제한은 compliance 소유자만 걸 수 있다', async () => {
    const {
      suite: { token },
      accounts: { aliceWallet },
    } = await loadFixture(deployFullSuiteFixture);
    const compliance = await ethers.deployContract('CountryRestrictionsTest');
    await token.setCompliance(compliance.address);
    await expect(compliance.connect(aliceWallet).addCountryRestriction(410)).to.be.reverted;
  });
});
